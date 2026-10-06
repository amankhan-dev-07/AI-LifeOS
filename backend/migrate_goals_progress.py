from sqlalchemy import create_engine, text
from app.config.settings import settings

eng = create_engine(settings.DATABASE_URL)
with eng.begin() as c:
    cols = [r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='goals'")).fetchall()]
    print("before", cols)
    if "progress" not in cols:
        c.execute(text("ALTER TABLE goals ADD COLUMN progress INTEGER NOT NULL DEFAULT 0"))
        print("added progress")
        c.execute(text("UPDATE goals SET progress=100 WHERE is_completed=true"))
        c.execute(text("UPDATE goals SET progress=0 WHERE is_completed=false"))
        print("seeded")
    else:
        print("already exists")
    cols2 = [r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='goals'")).fetchall()]
    print("after", cols2)
    rows = list(c.execute(text("SELECT id, title, progress, is_completed FROM goals LIMIT 5")))
    print(rows)
