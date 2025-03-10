# Budget Tracker

A Django-based personal budget tracking application that helps users manage their finances by tracking income, expenses, and budget allocations across different categories.

## Features

- Multi-user support with secure authentication
- Google OAuth 2.0 login integration
- Income tracking with support for different payment frequencies
- Budget creation and management
- Transaction tracking and history
- Recurring transactions
- Budget vs. Actual spending visualization
- Customizable budget categories
- Budget rollover support
- Mobile-responsive design

## Tech Stack

- Python 3.12+
- Django 5.1+
- Bootstrap 5.3
- Chart.js 4.4
- SQLite (default) / PostgreSQL (production)
- SortableJS for drag-and-drop functionality
- Python Social Auth for OAuth integration

## Local Development Setup

1. Clone the repository
```bash
git clone
cd budget-tracker
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up Google OAuth 2.0 (Required for Google Login)
   - Follow the [Integrating Google Sign-In into your web app](https://developers.google.com/identity/sign-in/web/sign-in) guide to create a project
   - Add authorized origins and redirect URIs:
      - For local development:
        - Origin: `http://localhost:8000`
        - Redirect URI: `http://localhost:8000/oauth/complete/google-oauth2/`
      - For production:
        - Origin: `https://your-domain.com`
        - Redirect URI: `https://your-domain.com/oauth/complete/google-oauth2/`
   - Copy your Client ID and Client Secret

5. Run migrations
```bash
python manage.py migrate
```

6. Create a superuser (optional)
```bash
python manage.py createsuperuser
```

7. Run the development server
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=.vercel.app,your-domain.com
DATABASE_URL=your-database-url  # For PostgreSQL in production
GOOGLE_OAUTH2_KEY=your-google-client-id
GOOGLE_OAUTH2_SECRET=your-google-client-secret
```

You can use `python -c 'import secrets; print(secrets.token_hex(100))` to generate your secret key.

## Deployment on Vercel & Neon

To host this project in the cloud, Neon (DB) & Vercel (Backend) can be used.

### Create Neon Project
1. Sign up or login to [Neon](https://neon.tech/)
2. Create the budget_tracker project
3. Copy the database URL provided - this will be used in your environment variables

### Create Vercel Application
1. Sign up or login to [Vercel](https://vercel.app).
2. Import your forked repository in the Vercel dashboard, or link to main.
3. Add the environment variables from the section above to your apps configuration.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details