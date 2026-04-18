package config

import (
	"os"
	"strings"
)

type Config struct {
	Port         string
	MongoURI     string
	MongoDB      string
	AIServiceURL string
	CORSOrigins  []string
}

func Load() Config {
	return Config{
		Port:         getenv("BACKEND_PORT", "8080"),
		MongoURI:     getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/mbti?authSource=admin"),
		MongoDB:      getenv("MONGO_DB", "mbti"),
		AIServiceURL: getenv("AI_SERVICE_URL", "http://localhost:8000"),
		CORSOrigins:  strings.Split(getenv("CORS_ORIGINS", "http://localhost:4200"), ","),
	}
}

func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
