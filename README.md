# Elasto Mania Stats Combine

This repository, including this README file, is almost completely AI-generated. Sorry for the bad code. Didn't have time at the lan party to design this properly.

A web application that combines Elasto Mania player statistics from multiple STATE.DAT files. This tool allows players to upload their personal STATE.DAT files and combines everyone's best times to create a comprehensive leaderboard.

![Elasto Mania](static/elma.jpg)

## Features

- Upload Elasto Mania STATE.DAT files to contribute personal best times
- View combined leaderboard showing everyone's best times
- Track detailed statistics for each player and level
- Calculate combined best results using the top time from any player for each level
- Finnish language interface

## Requirements

- Python 3.6+
- Flask web framework
- elma-python library for parsing Elasto Mania data files

## Project Structure

- `main.py`: The main Flask application
- `requirements.txt`: Python dependencies
- `templates/`: HTML templates for the web interface
- `static/`: Static files (images, CSS)
- `uploads/`: Temporary storage for uploaded STATE.DAT files
- `state_store/`: Permanent storage for processed STATE.DAT files

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/tumik/elma-lanparty-stats.git
cd elma-lanparty-stats
git submodule update --init
```

### 2. Create a Virtual Environment

#### On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

#### On macOS/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python main.py
```

The application will start running at http://localhost:5000.

## Usage

1. Navigate to http://localhost:5000 in your web browser
2. Upload your STATE.DAT file from your Elasto Mania installation
3. View the combined statistics on the main page

## Deployment

For production deployment, consider using a WSGI server like Gunicorn and a reverse proxy like Nginx.

Example with Gunicorn:

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

## License

This project uses elma-python library licensed under MIT. See the LICENSE file in the elma-python directory for details.

## Credits

- Elasto Mania game by Balázs Rózsa
- elma-python library for parsing Elasto Mania files
- Flask web framework
