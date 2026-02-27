# Store Manager

A professional, production-ready Flask-based store management system with customer and transaction tracking.

## Features

✅ **Authentication & Security**
- Secure admin login/register with password hashing
- Session management with login protection
- Default admin account (`admin`/`admin123`)

✅ **Customer Management**
- Click customer name to view full profile with:
  - Contact information (phone, address)
  - Custom notes and extra info fields
  - Outstanding loan tracking
  - Transaction history
- Auto-create customer profiles on first transaction

✅ **Transaction Management**
- Record store transactions (product, quantity, unit price)
- All amounts in Rwandan Francs (RWF)
- Auto-calculate totals and outstanding loans
- Edit and delete transactions safely
- Search transactions by customer name

✅ **Dashboard Analytics**
- Total sales summary (RWF)
- Total outstanding loans (RWF)
- Active customer count
- Clean, responsive dark-themed UI

✅ **Loan Tracking**
- Automatic loan calculation (total - paid)
- View outstanding loans per customer
- Color-coded loan status (red for debt, green for paid)
- Summary of total loans in customer profile

✅ **Technical**
- SQLite database with migration support
- Safe form input handling with RWF whole-number support
- Secure password hashing (Werkzeug)
- Jinja2 templates with flash messages
- Production-ready error handling

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Access the app:**
   Open http://127.0.0.1:5000 in your browser

4. **Login:**
   - Username: `admin`
   - Password: `admin123`

## Project Structure

```
.
├── app.py                 # Flask application
├── store.db              # SQLite database (auto-created)
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── templates/
    ├── login.html        # Admin login page
    ├── register.html     # Admin registration page
    ├── index.html        # Dashboard with records & add form
    ├── customer.html     # Customer profile & transaction history
    └── edit.html         # Edit transaction form
```

## Database Schema

### users
- `id` (PK)
- `username` (unique)
- `password` (hashed)

### customers
- `id` (PK)
- `full_name` (unique)
- `phone`
- `address`
- `note`
- `created_at`

### records
- `id` (PK)
- `customer_id` (FK)
- `product`
- `quantity` (real)
- `unit_price` (real)
- `total` (calculated)
- `paid` (real)
- `loan` (calculated: total - paid)
- `date`

## Usage Guide

### Adding a Transaction
1. Log in to the dashboard
2. Fill in customer name, product, quantity, unit price, and paid amount
3. Total and loan are calculated automatically
4. Click "Add"

### Viewing Customer Profile
- Click on any customer name in the dashboard to view their profile
- Edit customer contact information and notes
- View all transactions for that customer

### Editing/Deleting Records
- Click "Edit" to modify transaction details
- Click "Delete" to remove a transaction (with confirmation)

### Searching
- Use the search bar to find transactions by customer name

### Creating Additional Admins
1. Log out from the login page
2. Click "Register here"
3. Create new admin account
4. Log in with new credentials

## Deployment

### Local Development
```bash
python app.py
```

### Production with Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker
A `Dockerfile` is included for containerization. Build and run:
```bash
docker build -t store-manager .
docker run -p 5000:5000 store-manager
```

### Environment Variables
- `FLASK_ENV` - Set to `production` for production deployments
- `SECRET_KEY` - Change the secret key in `app.py` for production

## Security Notes

⚠️ **Before Production:**
1. Change `app.secret_key` in `app.py` to a strong random value
2. Set `debug=False` when deploying
3. Use environment variables for sensitive config
4. Ensure HTTPS is enabled
5. Regularly back up `store.db`

## Technical Specifications

- **Framework:** Flask 3.0.0
- **Database:** SQLite
- **ORM:** Native sqlite3 (no ORM dependency)
- **Authentication:** Werkzeug password hashing
- **Templates:** Jinja2
- **Server:** Gunicorn (production)

## Maintenance

### Database Backup
```bash
cp store.db store.db.backup
```

### Database Reset
Delete `store.db` and restart the app to initialize fresh.

### Logs
Flask development server logs to console. Use a proper logging setup for production.

## Troubleshooting

**Template not found error:**
- Ensure `templates/` directory exists with all HTML files

**Database locked error:**
- SQLite doesn't support concurrent writes well; use PostgreSQL for production

**Login fails:**
- Verify admin account exists: check `store.db`
- Reset default admin by deleting `store.db` and restarting

## Future Enhancements

- [ ] Multi-currency support
- [ ] Invoice generation (PDF)
- [ ] SMS/Email notifications
- [ ] Advanced analytics and reports
- [ ] User roles (manager, viewer, etc.)
- [ ] Bulk upload (CSV)

## License

MIT License - Feel free to use for personal or commercial projects.

## Support

For issues or questions, review the code or contact your development team.

