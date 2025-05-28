CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    test_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    status TEXT NOT NULL,
    result TEXT,
    details TEXT,
    connection_status TEXT
);
