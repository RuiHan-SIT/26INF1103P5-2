# AI Handover Assistant

INF1103 Programming Project (Group P5-2)

When someone leaves, goes on leave or moves to another role, they usually write a handover for whoever is taking over their work. These notes are often messy and miss things like who owns a task or when it's due. Our program takes the handover notes, uses Gemini to sort them into outstanding tasks, routine (BAU) tasks and important info, and makes sure every task has an owner and a proper deadline before it gets saved. The person taking over can then pull up the handover using the previous employee's ID.

## How to use it

Run the program and pick an option from the menu:

1. **Create a new handover** - enter your employee ID, then type your handover notes, use `file:<filename>` to load a .txt file from `data/handovers/`, or drag a .txt file into the terminal. If anything is missing (owner, deadline, etc.) the program will ask you to fill it in. Once it's complete, it's saved to `data/handovers.json` and a summary .txt is created in `data/summaries/`.
2. **View a handover** - enter the ID of the person who handed over, then your own ID. You'll see their latest handover and who has viewed it before. Your view gets added to the history.
3. **Delete a handover** - enter your ID, choose which of your handovers to delete and confirm. Both the saved record and the summary file are removed.

Note: you can only use employee IDs that are in `data/employees.json`.

A few rules the program checks:
- Handovers can't contain sensitive info like NRIC/FIN, passport numbers, emails or passwords
- Files have to be .txt, not empty, and under 5MB
- Outstanding tasks need a task name, description, owner and a deadline (DD/MM/YYYY, today or later)
- Routine tasks need a task name, description and owner

## Setup

1. Install the libraries (we recommend using a virtual environment):
```
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```

2. Make a copy of `.env.example`, rename it to `.env` and put your Gemini API key in it:
```
GEMINI_API_KEY=your-key-here
```
Don't commit your `.env` file! It's already in `.gitignore`.

## Running the program

From the project folder:
```
python src/main.py
```

### Running the tests
```
python -m pytest -v
```
The tests don't call Gemini, the AI responses are mocked. More details on the test cases are in `tests/README.md`.

## Docker

Make sure Docker Desktop is open first.

To pull the latest changes and build the image (this also runs the tests):
```
powershell -ExecutionPolicy Bypass -File .\update.ps1
```

To run the program:
```
docker run --rm -it --env-file .env -v "${PWD}/data:/app/data" handover-app
```
Keep the `-v` part in, otherwise anything you save is gone once the container stops.

To run only the tests in Docker:
```
docker run --rm handover-app pytest -v
```

## Project structure

```text
26INF1103P5-2/
├── .env.example                 # template for your .env file
├── Dockerfile
├── update.ps1                   # pulls latest code and builds the docker image
├── requirements.txt
├── ProjectInitialDetails.md     # problem statement and business rules
│
├── src/
│   ├── main.py                  # main menu and program flow
│   ├── offline_demo.py          # runs the program without calling the API
│   ├── prepare_offline_response.py
│   ├── model/
│   │   └── handover_model.py    # pydantic schema for the AI output
│   ├── modules/
│   │   ├── input_handler.py     # user input, file checks, sensitive info detection
│   │   ├── gemini_router.py     # sends the handover to Gemini and checks the response
│   │   ├── logic_manager.py     # checks required fields and deadlines, sorts tasks
│   │   ├── data_manager.py      # saves, reads, updates and deletes handovers
│   │   └── output.py            # prints results and creates the summary .txt files
│   └── utils/
│       ├── config.py            # file paths
│       ├── gemini_client.py     # Gemini API setup
│       ├── llm_prompt.py        # prompt for the AI
│       └── logger.py
│
├── data/
│   ├── employees.json           # list of employees that can use the program
│   ├── handovers/               # sample handover .txt files
│   ├── offline_responses/       # saved AI responses for the offline demo
│   ├── handovers.json           # saved handovers (not committed)
│   └── summaries/               # summary .txt files (not committed)
│
└── tests/                       # pytest test files
```

## For the team

- If you add a new library, remember to add it to `requirements.txt`
- Pull before you start working and before you push
