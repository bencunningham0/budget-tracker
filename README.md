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
   1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
   2. Create a new project or select an existing one
   3. Enable the Google+ API or Google People API
   4. Go to Credentials and create an OAuth 2.0 Client ID
   5. Configure the OAuth consent screen
   6. Add authorized origins and redirect URIs:
      - For local development:
        - Origin: `http://localhost:8000`
        - Redirect URI: `http://localhost:8000/oauth/complete/google-oauth2/`
      - For production:
        - Origin: `https://your-app-name.vercel.app`
        - Redirect URI: `https://your-app-name.vercel.app/oauth/complete/google-oauth2/`
   7. Copy your Client ID and Client Secret

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

## Deployment on Vercel

### Option 1: Using Vercel CLI
1. Install Vercel CLI
```bash
npm i -g vercel
```

2. Build the project locally
```bash
pip install -r requirements.txt
python manage.py collectstatic
```

3. Deploy to Vercel
```bash
vercel
```

### Option 2: Using Vercel Web Interface
1. Import your repository in the Vercel dashboard
2. Configure the build settings:
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - Output Directory: `staticfiles`
   - Install Command: `pip install -r requirements.txt`
3. Add the following environment variables in your Vercel project settings:
   - `DEBUG`: `False`
   - `SECRET_KEY`: [your-secret-key]
   - `ALLOWED_HOSTS`: [your-vercel-domain]
   - `DATABASE_URL`: [your-database-url]
   - `GOOGLE_OAUTH2_KEY`: [your-google-client-id]
   - `GOOGLE_OAUTH2_SECRET`: [your-google-client-secret]

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details