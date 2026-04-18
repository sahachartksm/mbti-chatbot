package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	"github.com/mbti-chatbot/backend/ai"
	"github.com/mbti-chatbot/backend/config"
	"github.com/mbti-chatbot/backend/db"
	"github.com/mbti-chatbot/backend/handlers"
)

func main() {
	cfg := config.Load()
	log.Printf("[boot] Port=%s Mongo=%s AI=%s", cfg.Port, mask(cfg.MongoURI), cfg.AIServiceURL)

	// 1. Mongo
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	repo, err := db.NewMongo(ctx, cfg.MongoURI, cfg.MongoDB)
	if err != nil {
		log.Fatalf("[fatal] cannot connect mongodb: %v", err)
	}
	log.Println("✓ MongoDB connected")

	// 2. AI
	aiClient := ai.NewClient(cfg.AIServiceURL)
	if err := aiClient.Health(ctx); err != nil {
		log.Printf("⚠ AI service not reachable yet: %v (will retry per-request)", err)
	} else {
		log.Println("✓ AI service reachable")
	}

	// 3. Router
	h := handlers.New(repo, aiClient)
	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   cfg.CORSOrigins,
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-Request-Id"},
		AllowCredentials: false,
		MaxAge:           300,
	}))

	r.Route("/api", func(r chi.Router) {
		r.Get("/health", h.Health)
		r.Get("/stats", h.Stats)
		r.Post("/session/start", h.StartSession)
		r.Get("/session/{id}", h.GetSession)
		r.Post("/session/{id}/answer", h.AddAnswer)
		r.Post("/session/{id}/analyze", h.Analyze)
		r.Get("/session/{id}/result", h.GetResult)
	})

	// 4. Server with graceful shutdown
	srv := &http.Server{
		Addr:              ":" + cfg.Port,
		Handler:           r,
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		log.Printf("🚀 Go server listening on :%s", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[fatal] server: %v", err)
		}
	}()

	// shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("shutting down...")
	shCtx, shCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shCancel()
	_ = srv.Shutdown(shCtx)
	log.Println("bye")
}

func mask(uri string) string {
	if len(uri) < 30 {
		return uri
	}
	return uri[:20] + "..." + uri[len(uri)-10:]
}
