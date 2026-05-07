import aiosqlite
import json
import os
import logging

# Ensure the database path is absolute relative to this file to prevent issues on different hosters
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "GVRY_database.db")

class Database:
    @staticmethod
    async def initialize():
        """Initializes the database tables and migrates JSON data if necessary."""
        async with aiosqlite.connect(DB_PATH, check_same_thread=False) as db:
            # Economy Table
            await db.execute('''CREATE TABLE IF NOT EXISTS economy (
                user_id TEXT PRIMARY KEY,
                wallet INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                last_work REAL DEFAULT 0,
                last_crime REAL DEFAULT 0,
                last_collect REAL DEFAULT 0,
                roblox_id TEXT,
                roblox_username TEXT
            )''')

            # Vehicles Table
            await db.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                year TEXT,
                make TEXT,
                model TEXT,
                color TEXT,
                plate TEXT
            )''')

            # Citations Table
            await db.execute('''CREATE TABLE IF NOT EXISTS citations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                department TEXT,
                reason TEXT,
                penal_code TEXT,
                price INTEGER,
                officer_id TEXT,
                status TEXT,
                message_id TEXT,
                vehicle_make TEXT,
                vehicle_model TEXT,
                vehicle_color TEXT,
                vehicle_plate TEXT
            )''')

            # Moderation Table
            await db.execute('''CREATE TABLE IF NOT EXISTS moderation (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                type TEXT, -- 'infraction', 'strike', 'ban'
                reason TEXT,
                proof TEXT,
                moderator_id TEXT,
                timestamp TEXT,
                cleared BOOLEAN DEFAULT 0,
                cleared_by TEXT,
                cleared_reason TEXT
            )''')

            # Staff Sessions Table
            await db.execute('''CREATE TABLE IF NOT EXISTS staff_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                session_type TEXT, -- 'Host' or 'Co-Host'
                session_date TEXT,
                start_time TEXT,
                end_time TEXT,
                notes TEXT
            )''')

            await db.commit()
        
        # Optional: Run migration from JSON to DB if files exist
        await Database._migrate_json_data()

    @staticmethod
    async def _migrate_json_data():
        """Migrates data from existing JSON files into the SQLite database."""
        async with aiosqlite.connect(DB_PATH, check_same_thread=False) as db:
            # 1. Migrate Economy
            econ_json = os.path.join(BASE_DIR, "economy.json")
            if os.path.exists(econ_json):
                try:
                    with open(econ_json, "r") as f:
                        data = json.load(f)
                    for user_id, stats in data.items():
                        await db.execute(
                            "INSERT OR IGNORE INTO economy (user_id, wallet, bank, last_work, last_crime, last_collect) VALUES (?, ?, ?, ?, ?, ?)",
                            (user_id, stats.get('wallet', 0), stats.get('bank', 0), stats.get('last_work', 0), stats.get('last_crime', 0), stats.get('last_collect', 0))
                        )
                    logging.info("Migrated economy.json to database.")
                    os.rename(econ_json, econ_json + ".backup")
                except Exception as e:
                    logging.error(f"Error migrating economy: {e}")

            # 2. Migrate Vehicles
            veh_json = os.path.join(BASE_DIR, "vehicle_registrations.json")
            if os.path.exists(veh_json):
                try:
                    with open(veh_json, "r") as f:
                        data = json.load(f)
                    for user_id, profile in data.items():
                        for v in profile.get("vehicles", []):
                            await db.execute(
                                "INSERT INTO vehicles (user_id, year, make, model, color, plate) VALUES (?, ?, ?, ?, ?, ?)",
                                (user_id, v.get('year'), v.get('make'), v.get('model'), v.get('color'), v.get('plate'))
                            )
                    logging.info("Migrated vehicle_registrations.json to database.")
                    os.rename(veh_json, veh_json + ".backup")
                except Exception as e:
                    logging.error(f"Error migrating vehicles: {e}")

            # 3. Migrate Citations
            cit_json = os.path.join(BASE_DIR, "citations.json")
            if os.path.exists(cit_json):
                try:
                    with open(cit_json, "r") as f:
                        data = json.load(f)
                    for user_id, user_citations in data.items():
                        for c in user_citations:
                            await db.execute(
                                "INSERT OR IGNORE INTO citations (id, user_id, department, reason, penal_code, price, officer_id, status, message_id, vehicle_make, vehicle_model, vehicle_color, vehicle_plate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (c.get('id'), user_id, c.get('department'), c.get('reason'), c.get('penal_code'), c.get('price'), str(c.get('officer_id')), c.get('status'), str(c.get('message_id')), None, None, None, None)
                            )
                    logging.info("Migrated citations.json to database.")
                    os.rename(cit_json, cit_json + ".backup")
                except Exception as e:
                    logging.error(f"Error migrating citations: {e}")

            # 4. Migrate Moderation (Infractions, Strikes, Bans)
            mod_json = os.path.join(BASE_DIR, "moderation.json")
            if os.path.exists(mod_json):
                try:
                    with open(mod_json, "r") as f:
                        data = json.load(f)
                    for user_id, logs in data.items():
                        # Infractions
                        for inf in logs.get("infractions", []):
                            await db.execute(
                                "INSERT OR IGNORE INTO moderation (id, user_id, type, reason, proof, moderator_id, timestamp, cleared, cleared_by, cleared_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (inf.get('id'), user_id, 'infraction', inf.get('reason'), inf.get('proof'), str(inf.get('moderator_id')), inf.get('timestamp'), 1 if inf.get('cleared') else 0, str(inf.get('cleared_by')), inf.get('cleared_reason'))
                            )
                        # Strikes
                        for strk in logs.get("strikes", []):
                            await db.execute(
                                "INSERT OR IGNORE INTO moderation (id, user_id, type, reason, proof, moderator_id, timestamp, cleared, cleared_by, cleared_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (strk.get('id'), user_id, 'strike', strk.get('reason'), strk.get('proof'), str(strk.get('moderator_id')), strk.get('timestamp'), 1 if strk.get('cleared') else 0, str(strk.get('cleared_by')), strk.get('cleared_reason'))
                            )
                        # Bans
                        for ban in logs.get("bans", []):
                            import uuid # For temporary IDs for bans which didn't have them in JSON
                            ban_id = f"BAN-{uuid.uuid4().hex[:6].upper()}"
                            await db.execute(
                                "INSERT OR IGNORE INTO moderation (id, user_id, type, reason, proof, moderator_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (ban_id, user_id, 'ban', ban.get('reason'), ban.get('proof'), str(ban.get('moderator_id')), ban.get('timestamp'))
                            )
                    logging.info("Migrated moderation.json to database.")
                    os.rename(mod_json, mod_json + ".backup")
                except Exception as e:
                    logging.error(f"Error migrating moderation: {e}")

            # 5. Migrate Staff Data
            staff_json = os.path.join(BASE_DIR, "staff_data.json")
            if os.path.exists(staff_json):
                try:
                    with open(staff_json, "r") as f:
                        data = json.load(f)
                    for user_id, stats in data.items():
                        for s in stats.get("hosted", []):
                            await db.execute(
                                "INSERT INTO staff_sessions (user_id, session_type, session_date, start_time, end_time, notes) VALUES (?, ?, ?, ?, ?, ?)",
                                (user_id, "Host", s.get("date"), s.get("start"), s.get("end"), s.get("notes")))
                        for s in stats.get("cohosted", []):
                            await db.execute(
                                "INSERT INTO staff_sessions (user_id, session_type, session_date, start_time, end_time, notes) VALUES (?, ?, ?, ?, ?, ?)",
                                (user_id, "Co-Host", s.get("date"), s.get("start"), s.get("end"), s.get("notes")))
                    logging.info("Migrated staff_data.json to database.")
                    os.rename(staff_json, staff_json + ".backup")
                except Exception as e:
                    logging.error(f"Error migrating staff data: {e}")

            await db.commit()

    @staticmethod
    async def fetch_all(query: str, parameters: tuple = ()):
        async with aiosqlite.connect(DB_PATH, check_same_thread=False) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, parameters) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    @staticmethod
    async def fetch_one(query: str, parameters: tuple = ()):
        async with aiosqlite.connect(DB_PATH, check_same_thread=False) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, parameters) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    @staticmethod
    async def execute(query: str, parameters: tuple = ()):
        try:
            async with aiosqlite.connect(DB_PATH, check_same_thread=False) as db:
                await db.execute(query, parameters)
                await db.commit()
        except Exception as e:
            logging.error(f"Database Execution Error: {e}")
            logging.error(f"Query: {query}")
            raise e

    # Specific helpers for profile.py
    @staticmethod
    async def get_vehicle_count(user_id: str):
        res = await Database.fetch_one("SELECT COUNT(*) as count FROM vehicles WHERE user_id = ?", (user_id,))
        return res['count'] if res else 0

    @staticmethod
    async def get_citation_count(user_id: str):
        res = await Database.fetch_one("SELECT COUNT(*) as count FROM citations WHERE user_id = ?", (user_id,))
        return res['count'] if res else 0