# O2 On Demand Hack

This project automates 2GB data add-on via SMS for O2's Unlimited On Demand service after 10GB limit.
You can check here for supported Huawei LTE/5G modems: https://github.com/Salamek/huawei-lte-api

## Installation

1. **Clone the Repository:**
    ```bash
    git clone https://github.com/e-onux/o2-on-demand-sms-sendery
    cd O2-On-Demand-Hack
    ```

2. **Set Up Python Environment:**
    It's recommended to use a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install Requirements:**
    Install the required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1. **Environment Variables:**
    Rename the `.env.example` file to `.env` and edit it to include your credentials:
    ```bash
    mv .env.example .env
    ```
    Then, open `.env` and update the following entries:
    ```
    API_USER=your_username_here
    API_PASSWORD=your_password_here
    ```

## Usage

Run the script to interact with the modem:
```
python o2_on_demand_hack.py
```

## Contributing

Feel free to fork this repository and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License see the LICENSE file for details.