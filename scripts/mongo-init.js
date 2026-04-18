// Initial MongoDB setup — runs once on first container boot
db = db.getSiblingDB('mbti');

db.createCollection('sessions');
db.createCollection('results');

db.sessions.createIndex({ session_id: 1 }, { unique: true });
db.sessions.createIndex({ created_at: 1 });
db.results.createIndex({ session_id: 1 });
db.results.createIndex({ mbti_type: 1 });
db.results.createIndex({ created_at: -1 });

print('✓ MBTI database initialized with indexes');
