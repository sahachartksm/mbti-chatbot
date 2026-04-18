package db

import (
	"context"
	"errors"
	"time"

	"github.com/mbti-chatbot/backend/models"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// ErrNotFound — returned when session is not found
var ErrNotFound = errors.New("session not found")

// Repository — interface to abstract data layer (test-friendly)
type Repository interface {
	Ping(ctx context.Context) error
	CreateSession(ctx context.Context, s *models.Session) error
	GetSession(ctx context.Context, id string) (*models.Session, error)
	AddAnswer(ctx context.Context, id string, ans models.Answer) (*models.Session, error)
	MarkAnalyzed(ctx context.Context, id string) error
	SaveResult(ctx context.Context, r *models.Result) error
	GetResult(ctx context.Context, sessionID string) (*models.Result, error)
	TypeDistribution(ctx context.Context) (map[string]int64, error)
}

type MongoRepo struct {
	client   *mongo.Client
	sessions *mongo.Collection
	results  *mongo.Collection
}

func NewMongo(ctx context.Context, uri, dbname string) (*MongoRepo, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		return nil, err
	}
	if err := client.Ping(ctx, nil); err != nil {
		return nil, err
	}
	d := client.Database(dbname)
	return &MongoRepo{
		client:   client,
		sessions: d.Collection("sessions"),
		results:  d.Collection("results"),
	}, nil
}

func (r *MongoRepo) Ping(ctx context.Context) error {
	return r.client.Ping(ctx, nil)
}

func (r *MongoRepo) CreateSession(ctx context.Context, s *models.Session) error {
	_, err := r.sessions.InsertOne(ctx, s)
	return err
}

func (r *MongoRepo) GetSession(ctx context.Context, id string) (*models.Session, error) {
	var s models.Session
	err := r.sessions.FindOne(ctx, bson.M{"session_id": id}).Decode(&s)
	if errors.Is(err, mongo.ErrNoDocuments) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &s, nil
}

func (r *MongoRepo) AddAnswer(ctx context.Context, id string, ans models.Answer) (*models.Session, error) {
	// pull old answer of same question_id (upsert-style replace)
	_, _ = r.sessions.UpdateOne(ctx,
		bson.M{"session_id": id},
		bson.M{"$pull": bson.M{"answers": bson.M{"question_id": ans.QuestionID}}},
	)
	res, err := r.sessions.UpdateOne(ctx,
		bson.M{"session_id": id},
		bson.M{"$push": bson.M{"answers": ans}},
	)
	if err != nil {
		return nil, err
	}
	if res.MatchedCount == 0 {
		return nil, ErrNotFound
	}
	return r.GetSession(ctx, id)
}

func (r *MongoRepo) MarkAnalyzed(ctx context.Context, id string) error {
	_, err := r.sessions.UpdateOne(ctx,
		bson.M{"session_id": id},
		bson.M{"$set": bson.M{"analyzed": true, "analyzed_at": time.Now().UTC()}},
	)
	return err
}

func (r *MongoRepo) SaveResult(ctx context.Context, res *models.Result) error {
	_, err := r.results.UpdateOne(ctx,
		bson.M{"session_id": res.SessionID},
		bson.M{"$set": res},
		options.Update().SetUpsert(true),
	)
	return err
}

func (r *MongoRepo) GetResult(ctx context.Context, sessionID string) (*models.Result, error) {
	var res models.Result
	err := r.results.FindOne(ctx, bson.M{"session_id": sessionID}).Decode(&res)
	if errors.Is(err, mongo.ErrNoDocuments) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &res, nil
}

func (r *MongoRepo) TypeDistribution(ctx context.Context) (map[string]int64, error) {
	cursor, err := r.results.Aggregate(ctx, bson.A{
		bson.M{"$group": bson.M{"_id": "$mbti_type", "count": bson.M{"$sum": 1}}},
	})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)
	out := make(map[string]int64)
	for cursor.Next(ctx) {
		var row struct {
			ID    string `bson:"_id"`
			Count int64  `bson:"count"`
		}
		if err := cursor.Decode(&row); err != nil {
			return nil, err
		}
		out[row.ID] = row.Count
	}
	return out, nil
}
