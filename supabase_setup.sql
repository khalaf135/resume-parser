-- =============================================
-- JADEER PLATFORM - DATABASE SETUP
-- Run this SQL in your Supabase SQL Editor
-- =============================================

-- 1. Create user_roles table
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    role TEXT CHECK (role IN ('candidate', 'employer')) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create candidate_profiles table
CREATE TABLE IF NOT EXISTS candidate_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    full_name TEXT,
    professional_headline TEXT,
    location TEXT,
    phone TEXT,
    major_specialization TEXT,
    graduation_year INTEGER,
    years_of_experience TEXT,
    preferred_job_type TEXT,
    bio TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create employer_profiles table
CREATE TABLE IF NOT EXISTS employer_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    full_name TEXT,
    role_title TEXT,
    company_name TEXT,
    location TEXT,
    phone TEXT,
    company_website TEXT,
    company_description TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create skills table
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    skill_name TEXT NOT NULL,
    skill_type TEXT CHECK (skill_type IN ('soft', 'technical')) NOT NULL,
    score INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    assessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create certificates table
CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    certificate_name TEXT NOT NULL,
    issuing_organization TEXT,
    issue_date DATE,
    credential_id TEXT,
    credential_url TEXT,
    file_path TEXT,
    status TEXT CHECK (status IN ('pending', 'verified', 'rejected', 'other')) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Modify existing cvs table (add columns if they don't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'cvs' AND column_name = 'is_primary') THEN
        ALTER TABLE cvs ADD COLUMN is_primary BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'cvs' AND column_name = 'title') THEN
        ALTER TABLE cvs ADD COLUMN title TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'cvs' AND column_name = 'tags') THEN
        ALTER TABLE cvs ADD COLUMN tags TEXT[];
    END IF;
END $$;

-- =============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================

-- Enable RLS on all tables
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE employer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE certificates ENABLE ROW LEVEL SECURITY;

-- user_roles policies
CREATE POLICY "Users can view own role" ON user_roles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own role" ON user_roles FOR INSERT WITH CHECK (auth.uid() = user_id);

-- candidate_profiles policies
CREATE POLICY "Users can view own candidate profile" ON candidate_profiles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Employers can view all candidate profiles" ON candidate_profiles FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'employer')
);
CREATE POLICY "Users can insert own candidate profile" ON candidate_profiles FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own candidate profile" ON candidate_profiles FOR UPDATE USING (auth.uid() = user_id);

-- employer_profiles policies
CREATE POLICY "Users can view own employer profile" ON employer_profiles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Candidates can view employer profiles" ON employer_profiles FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'candidate')
);
CREATE POLICY "Users can insert own employer profile" ON employer_profiles FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own employer profile" ON employer_profiles FOR UPDATE USING (auth.uid() = user_id);

-- skills policies
CREATE POLICY "Users can view own skills" ON skills FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Employers can view all skills" ON skills FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'employer')
);
CREATE POLICY "Users can manage own skills" ON skills FOR ALL USING (auth.uid() = user_id);

-- certificates policies
CREATE POLICY "Users can view own certificates" ON certificates FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Employers can view verified certificates" ON certificates FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'employer') AND status = 'verified'
);
CREATE POLICY "Users can manage own certificates" ON certificates FOR ALL USING (auth.uid() = user_id);

-- =============================================
-- DONE! Your database is now set up for Jadeer
-- =============================================
