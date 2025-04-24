from app import app, db, Achievement, ACHIEVEMENTS, User

def init_db():
    with app.app_context():
        # Drop all existing tables
        db.drop_all()
        
        # Create all tables with the current schema
        db.create_all()
        
        # Add achievements
        for achievement_data in ACHIEVEMENTS:
            achievement = Achievement(
                name=achievement_data['name'],
                description=achievement_data['description'],
                criteria=achievement_data['criteria']
            )
            db.session.add(achievement)
        
        # Create a test user
        test_user = User(
            username='test',
            email='test@example.com',
            daily_goal=30
        )
        test_user.set_password('test123')
        db.session.add(test_user)
        
        # Commit all changes
        db.session.commit()
        print("Database initialized successfully!")
        print("Test user created:")
        print("Username: test")
        print("Password: test123")

if __name__ == '__main__':
    init_db() 