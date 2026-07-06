-- Init script hanya untuk setup database
-- Tabel akan dibuat otomatis oleh SQLAlchemy

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Insert default genres hanya jika tabel songs sudah ada
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'songs') THEN
        -- Tidak perlu insert genre table karena kita pakai kolom genre di tabel songs
        RAISE NOTICE 'Tables ready for Karaoke System';
    END IF;
END $$;
