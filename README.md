# Inkspire Project

## Prerequisites

- Python 3.7 or higher
- Google AI API key (for Generative AI access)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <project-directory>
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_google_api_key_here
```

2. Obtain your Google AI API key:
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Generate a new API key
   - Add it to your `.env` file
