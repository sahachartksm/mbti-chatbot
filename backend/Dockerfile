# ====== Go Backend (chi + mongo-driver) ======
FROM golang:1.23-alpine

# Basic tooling
RUN apk add --no-cache git curl

WORKDIR /app

# Cache layer: download deps first
COPY go.mod go.sum* ./
RUN go mod download 2>/dev/null || true

# Copy source
COPY . ./

# Make sure go.sum exists + matches
RUN go mod tidy

EXPOSE 8080

# `go run .` rebuilds on container restart; for real hot reload use `air`
CMD ["sh", "-c", "go mod tidy && go run ."]
