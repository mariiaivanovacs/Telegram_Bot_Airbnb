# Telegram Bot for Airbnb Property Ratings

A Telegram bot that fetches property data from MockAPI and provides users with property ratings, details, and interactive features through simple commands.

## 🚀 Features

- **Property Listings**: View all properties with Airbnb & Booking ratings
- **Property Details**: Get detailed information for specific properties
- **Top Rated Properties**: See top 5 and top 20 properties with charts
- **Complaints System**: View complaints for specific properties
- **Interactive Menu**: User-friendly command interface
- **Real-time Data**: Fetches live data from MockAPI endpoints

## 📋 Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome message with interactive menu | `/start` |
| `/menu` | Show main menu with options | `/menu` |
| `/ratings` | List all properties with ratings | `/ratings` |
| `/top5` | Show top 5 rated properties with chart | `/top5` |
| `/top20` | Show top 20 rated properties with chart | `/top20` |
| `/properties` | List all properties (basic info) | `/properties` |
| `/property <id>` | Show single property details | `/property 1` |
| `/complaints <id>` | Show complaints for specific property | `/complaints 1` |

## 🛠️ Installation

### Prerequisites

- Python 3.7+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- MockAPI account and endpoint

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Telegram_Bot_Airbnb.git
   cd Telegram_Bot_Airbnb
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create `.env` file**
   ```bash
   cp .env.example .env
   ```

5. **Configure environment variables** (see Configuration section)

6. **Run the bot**
   ```bash
   python bot.py
   ```

## ⚙️ Configuration

Create a `.env` file in the project root with the following variables:

### Required Variables

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
MOCKAPI_URL=https://yourproject.mockapi.io/properties
```

### Optional Variables

```env
# Separate URL for properties list (defaults to MOCKAPI_URL)
PROPERTIES_URL=https://yourproject.mockapi.io/properties

# URL for complaints endpoint
COMPLAINTS_URL=https://yourproject.mockapi.io/complaints

# API authentication (if required by your MockAPI)
MOCKAPI_KEY=your_api_key_here
MOCKAPI_KEY_HEADER=Authorization
MOCKAPI_KEY_PREFIX=Bearer
```

### Getting Your Telegram Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the token provided by BotFather
5. Add it to your `.env` file

### Setting Up MockAPI

1. Go to [MockAPI.io](https://mockapi.io/)
2. Create a new project
3. Create endpoints for:
   - `/properties` - Array of property objects
   - `/complaints` - Array of complaint objects (optional)
4. Use the generated URL in your `.env` file

## 📊 Expected Data Format

### Property Object
```json
{
  "id": "1",
  "name": "Cozy Downtown Apartment",
  "location": "New York, NY",
  "airbnb_rating": 4.8,
  "booking_rating": 4.6,
  "price": 120,
  "description": "Beautiful apartment in the heart of the city"
}
```

### Complaint Object
```json
{
  "id": "1",
  "property_id": "1",
  "complaint": "Noise issues during night",
  "date": "2024-01-15",
  "status": "resolved"
}
```

## 🔧 Development

### Project Structure
```
Telegram_Bot_Airbnb/
├── bot.py              # Main bot application
├── README.md           # This file
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
├── .env               # Your environment variables (not in git)
└── venv/              # Virtual environment
```

### Key Functions

- `fetch_all_properties()` - Retrieves all properties from MockAPI
- `fetch_property_by_id(id)` - Gets specific property details
- `format_property(property)` - Formats property data for display
- `generate_ratings_chart()` - Creates rating comparison charts
- `split_and_send()` - Handles Telegram message length limits

### Adding New Commands

1. Create a handler function:
   ```python
   def my_command_handler(update, context):
       user = update.effective_user
       logger.info(f"User {user.first_name} used /mycommand")
       update.message.reply_text("Hello from my command!")
   ```

2. Register the handler in `main()`:
   ```python
   dp.add_handler(CommandHandler("mycommand", my_command_handler))
   ```

## 🚨 Troubleshooting

### Common Issues

**"Please set TELEGRAM_TOKEN and MOCKAPI_URL environment variables"**
- Check your `.env` file exists and has correct variable names
- Ensure `python-dotenv` is installed: `pip install python-dotenv`

**"No property data available"**
- Verify your MockAPI URL is correct and accessible
- Check MockAPI dashboard for endpoint configuration
- Test the URL directly in your browser

**Bot doesn't respond to commands**
- Verify bot token is correct
- Check if bot is running without errors
- Ensure bot has proper permissions in Telegram group (if applicable)

**Charts not generating**
- Install matplotlib: `pip install matplotlib`
- Check if properties have valid rating data

### Debug Mode

Enable detailed logging by modifying the logging level in `bot.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 📦 Dependencies

- `python-telegram-bot` - Telegram Bot API wrapper
- `requests` - HTTP library for API calls
- `python-dotenv` - Environment variable management
- `matplotlib` - Chart generation
- `numpy` - Numerical operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- Create an [issue](https://github.com/yourusername/Telegram_Bot_Airbnb/issues) for bug reports
- Join our [Telegram group](https://t.me/your_support_group) for community support
- Check the [Wiki](https://github.com/yourusername/Telegram_Bot_Airbnb/wiki) for additional documentation

## 🎯 Roadmap

- [ ] Add property search functionality
- [ ] Implement user favorites system
- [ ] Add property booking integration
- [ ] Create admin panel for property management
- [ ] Add multi-language support
- [ ] Implement user analytics dashboard

---
