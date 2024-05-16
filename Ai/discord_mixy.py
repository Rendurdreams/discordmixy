import requests
import json
from config import CMC_KEY, OPENAI_KEY, DISCORD_TOKEN, DISCORD_CHANNEL_ID
from openai import OpenAI
import os
import discord
from discord.ext import tasks, commands
import aiofiles
import signal
import sys

CMC_API_KEY = CMC_KEY
API_KEY = OPENAI_KEY
client = OpenAI(api_key=API_KEY)

discord_token = DISCORD_TOKEN
channel_id = DISCORD_CHANNEL_ID

intents = discord.Intents.default()
intents.messages = True  # Enable message content intent
intents.message_content = True  # Ensure message content intent is enabled
print(f"Intents: messages={intents.messages}, message_content={intents.message_content}")
bot = commands.Bot(command_prefix='!', intents=intents)

async def post_to_discord(message):
    channel = bot.get_channel(channel_id)
    if channel is None:
        print(f"Error: Channel ID {channel_id} not found.")
        return
    
    max_length = 2000
    sections = [message[i:i + max_length] for i in range(0, len(message), max_length)]
    for section in sections:
        await channel.send(section)

def fetch_crypto_data(api_key, ucids):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    parameters = {
        'id': ','.join(ucids),  # Convert list of UCIDs to a comma-separated string
        'convert': 'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key
    }

    response = requests.get(url, headers=headers, params=parameters)
    if response.status_code == 200:
        print("Successfully fetched cryptocurrency data.")
        return response.json()
    else:
        print(f"Failed to fetch cryptocurrency data. Status Code: {response.status_code}")
        return None

def fetch_latest_global_metrics(api_key):
    url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("Successfully fetched global metrics data.")
        return response.json()
    else:
        print(f"Failed to fetch global metrics data. Status Code: {response.status_code}")
        return None

def analyze_data_with_ai(crypto_data, global_metrics, sentiment, strategy):
    print("Mixy is analyzing the data, hold a sec and let the homie cook...")

    script_dir = os.path.dirname(os.path.realpath(__file__))
    sentiment_prompt_path = os.path.join(script_dir, f'{sentiment}.txt')
    strategy_file_path = os.path.join(script_dir, f'{strategy}.txt')

    try:
        sentiment_prompt = load_file(sentiment_prompt_path)
    except FileNotFoundError:
        print(f"Sentiment file '{sentiment_prompt_path}' not found.")
        return None

    print(f"Attempting to load strategy file from: {strategy_file_path}")

    try:
        strategy_prompt = load_file(strategy_file_path)
    except FileNotFoundError:
        print(f"Strategy file '{strategy_file_path}' not found.")
        return None

    # Create a dynamic prompt for GPT-4o
    prompt = f"""
    Yo bro, welcome to your ultimate crypto trading wingman! 
    I'm here to analyze market prices, global metrics, and all the juicy data from your database.
    We're on the lookout for trends, volume surges, and those wild price moves.
    
    ### Current Sentiment: {sentiment.capitalize()}
    - {sentiment_prompt}
    
    ### Strategy: {strategy.capitalize()}
    - {strategy_prompt}
    
    ### Cryptocurrency Data:
    {json.dumps(crypto_data, indent=4)}
    
    ### Global Metrics:
    {json.dumps(global_metrics, indent=4)}

    Let's get to work and make those trades count. Remember, it's all about staying sharp, adapting to the market, and having a blast while doing it. Let's roll, bro!
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a helpful assistant analyzing cryptocurrency data."},
                      {"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def load_file(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

async def save_analysis(analysis):
    async with aiofiles.open('previous_analyses.txt', 'a') as f:
        await f.write(analysis + '\n')

def check_repetitiveness(analysis):
    try:
        with open('previous_analyses.txt', 'r') as f:
            previous_analyses = f.readlines()
        if analysis + '\n' in previous_analyses[-10:]:  # Check the last 10 analyses for repetition
            return True
    except FileNotFoundError:
        pass
    return False

@tasks.loop(minutes=15)
async def main():
    # Read UCIDs from a file
    ucids = []
    try:
        with open('ucids.txt', 'r') as file:
            ucids = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print("The file ucids.txt was not found.")
        return

    # Define sentiment and strategy
    sentiment = 'bullish'  # This should be dynamic or read from a config in a real-world scenario
    strategy = 'strat1'    # This should be dynamic or read from a config in a real-world scenario

    crypto_data = fetch_crypto_data(CMC_API_KEY, ucids)
    global_metrics = fetch_latest_global_metrics(CMC_API_KEY)

    if crypto_data and global_metrics:
        analysis = analyze_data_with_ai(crypto_data.get('data', {}), global_metrics.get('data', {}), sentiment, strategy)
        if analysis:
            if not check_repetitiveness(analysis):
                await post_to_discord("AI Analysis:\n" + analysis)
                await save_analysis(analysis)
            else:
                print("Skipping repetitive analysis.")
        else:
            print("Failed to analyze data with AI.")
    else:
        print("Failed to fetch data for AI analysis.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    if not main.is_running():
        main.start()

@bot.command()
async def stop(ctx):
    await ctx.send("Bot is shutting down.")
    await bot.close()

def signal_handler(sig, frame):
    print('Exiting...')
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    bot.run(discord_token)
