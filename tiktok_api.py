import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import time
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import re

# Initialize lists
users = []
hashtag_id = []
hash_count = []
all_videos_info = []
all_challenge_info = []
all_creators_info = []

# Function to get TikTok users by hashtag
def get_tiktok_users_by_hashtag(hashtag, region='es'):
    driver = webdriver.Chrome()
    driver.maximize_window()
    url = f'https://www.tiktok.com/tag/{hashtag}?lang={region}'
    driver.get(url)
    time.sleep(5)
    page_source = driver.page_source

    user_elements = driver.find_elements(By.XPATH, "//p[@data-e2e='challenge-item-username']")
    for user_element in user_elements:
        users.append(user_element.text)

    soup = BeautifulSoup(page_source, 'html.parser')
    meta_tags = soup.find_all('meta')
    for meta_tag in meta_tags:
        content = meta_tag.get('content', '')
        if '://challenge/detail/' in content:
            pattern = r'://challenge/detail/(\d+)'
            match = re.search(pattern, content)
            if match:
                hashtag_id.append(match.group(1))
                break
    driver.quit()

# Function to get TikTok hashtag post counts
def get_tiktok_hashtag(hashtag, region='es'):
    driver = webdriver.Chrome()
    driver.maximize_window()
    url = f'https://www.tiktok.com/tag/{hashtag}?lang={region}'
    driver.get(url)
    time.sleep(3)
    try:
        user_elements = driver.find_elements(By.XPATH, "//h2[@data-e2e='challenge-vvcount']")
        if user_elements:
            for user_element in user_elements:
                hash_count.append(user_element.text)
        else:
            hash_count.append(0)
    except NoSuchElementException:
        hash_count.append(0)
    driver.quit()

# Example hashtags and obtaining post counts
hashtags = ["Whiteclaw", "HardSeltzer", "SummerVibes"]
for hashtag in hashtags:
    get_tiktok_hashtag(hashtag, region='es')
print(hash_count)

# Convert string to number
def convert_to_number(text):
    if isinstance(text, int):
        return text
    match = re.match(r'(\d+(?:\.\d+)?)([KM]?)', text)
    if not match:
        return 0
    number, suffix = match.groups()
    number = float(number)
    if suffix == 'K':
        return number * 1000
    elif suffix == 'M':
        return number * 1000000
    else:
        return number

hash_count_numbers = [convert_to_number(item.split()[0]) if isinstance(item, str) else item for item in hash_count]
data = pd.DataFrame({'hashtag': hashtags, 'post_count': hash_count_numbers})
top_10 = data.sort_values(by='post_count', ascending=False).head(20)

# Function to get TikTok video information
def get_tiktok_video_info():
    url = 'https://tiktok-scraper2.p.rapidapi.com/hashtag/videos'
    headers = {
        'x-rapidapi-host': '...',
        'x-rapidapi-key': '...'
    }

    for id in hashtag_id:
        querystring = {'hashtag_id': id, 'count': '30'}
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            data = response.json()
            videos = data.get('itemList', [])
            for video in videos:
                total_engagement = int(video['statsV2']['diggCount'], 0) + int(video['statsV2']['commentCount'], 0) + int(video['statsV2']['shareCount'], 0)
                view = int(video['statsV2']['playCount'], 0)
                engagement_rate = total_engagement / view * 100 if view != 0 else 0
                video_info = {
                    'video_id': video.get('id'),
                    'duration': video['music']['duration'],
                    'engagement_rate': engagement_rate,
                    'view_count': view,
                    'author_id': video['author']['id'],
                    'author_nickname': video['author']['nickname'],
                    'desc': video['desc']
                }
                all_videos_info.append(video_info)
        else:
            print(f"Request failed with status code {response.status_code}")

# Data Analysis
df = pd.DataFrame(all_videos_info)
df.dropna(inplace=True)
df['duration'] = df['duration'].astype(int)
df['view_count'] = df['view_count'].astype(int)

# Save plots
def save_plot(fig, filename):
    fig.savefig(filename, bbox_inches='tight')

# Set style and color palette
sns.set_style("whitegrid")
color_palette = sns.color_palette("viridis", as_cmap=True)

# Distribution Analysis
def plot_distribution(data, column, title, filename):
    fig, ax = plt.subplots()
    sns.histplot(data[column], kde=True, ax=ax, color=color_palette(0.2))
    ax.set_title(title, fontsize=15, fontweight='bold')
    ax.set_xlabel(column.replace('_', ' ').title(), fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    save_plot(fig, filename)

plot_distribution(df, 'duration', 'Duration Distribution', 'duration_distribution.png')
plot_distribution(df, 'engagement_rate', 'Engagement Rate Distribution', 'engagement_rate_distribution.png')
plot_distribution(df, 'view_count', 'View Count Distribution', 'view_count_distribution.png')

# Correlation Matrix
correlation_matrix = df[['duration', 'engagement_rate', 'view_count']].corr()
fig, ax = plt.subplots()
sns.heatmap(correlation_matrix, annot=True, cmap='viridis', ax=ax)
ax.set_title('Correlation Matrix', fontsize=15, fontweight='bold')
save_plot(fig, 'correlation_matrix.png')

# Scatter Plots with Regression Line
def plot_regression(data, x_col, y_col, title, filename):
    fig, ax = plt.subplots()
    sns.regplot(x=x_col, y=y_col, data=data, ax=ax, scatter_kws={"color": color_palette(0.2)}, line_kws={"color": color_palette(0.8)})
    ax.set_title(title, fontsize=15, fontweight='bold')
    ax.set_xlabel(x_col.replace('_', ' ').title(), fontsize=12)
    ax.set_ylabel(y_col.replace('_', ' ').title(), fontsize=12)
    save_plot(fig, filename)

plot_regression(df, 'duration', 'engagement_rate', 'Duration vs. Engagement Rate', 'duration_vs_engagement_rate.png')
plot_regression(df, 'view_count', 'engagement_rate', 'View Count vs. Engagement Rate', 'view_count_vs_engagement_rate.png')

# Word Cloud for Description
df['desc_word_count'] = df['desc'].apply(lambda x: len(x.split()))
plot_distribution(df, 'desc_word_count', 'Description Word Count Distribution', 'desc_word_count_distribution.png')

text = " ".join(desc for desc in df['desc'])
wordcloud = WordCloud(width=800, height=400, background_color='white', colormap='viridis').generate(text)
fig, ax = plt.subplots(figsize=(10, 5))
ax.imshow(wordcloud, interpolation='bilinear')
ax.axis('off')
ax.set_title('Word Cloud for Video Descriptions', fontsize=15, fontweight='bold')
save_plot(fig, 'word_cloud_descriptions.png')

plt.show()

# Function to get TikTok trending creators
def get_tiktok_trending_creators(region='es'):
    url = "https://scraptik.p.rapidapi.com/trending-creators"
    headers = {
        "x-rapidapi-host": "...",
        "x-rapidapi-key": "..."
    }
    response = requests.get(url, headers=headers, params={"region": region})
    if response.status_code == 200:
        data = response.json()
        user_list = data['user_list']
        for user in user_list:
            creator_info = {
                'creator_name': user['nickname'],
                'followers': user['follower_count'],
                'engagement': user['total_like_count']
            }
            all_creators_info.append(creator_info)
    else:
        print(f"Request failed with status code {response.status_code}")

# Function to get TikTok hashtag challenge info
def get_tiktok_challenge_info():
    url = "https://scraptik.p.rapidapi.com/category-list"
    headers = {
        "x-rapidapi-host": "...",
        "x-rapidapi-key": "..."
    }
    response = requests.get(url, headers=headers, params={"count": "25", "cursor": "0", "region": "es"})
    if response.status_code == 200:
        data = response.json()
        category_list = data['category_list']
        for category in category_list:
            challenge_info = {
                'challenge_name': category['challenge_info']['cha_name'],
                'user_count': category['challenge_info']['use_count'],
                'view_count': category['challenge_info']['view_count'],
                'desc': category['challenge_info']['desc']
            }
            all_challenge_info.append(challenge_info)
    else:
        print(f"Request failed with status code {response.status_code}")

# Example usage
for hashtag in top_10['hashtag']:
    get_tiktok_users_by_hashtag(hashtag, region='es')
get_tiktok_video_info()
get_tiktok_trending_creators(region='es')
get_tiktok_challenge_info()

# Visualization for Top 20 Hashtags
top_10 = data.sort_values(by='post_count', ascending=False).head(20)
norm = plt.Normalize(top_10['post_count'].min(), top_10['post_count'].max())
colors = plt.cm.viridis(norm(top_10['post_count']))

fig, ax = plt.subplots(figsize=(12, 8))
bars = ax.barh(top_10['hashtag'], top_10['post_count'], color=colors, edgecolor='black')
ax.set_xlabel('Post Count', fontsize=14)
ax.set_ylabel('Hashtag', fontsize=14)
ax.set_title('Top 20 Most Posted Hashtags related to Whiteclaw', fontsize=16)
ax.invert_yaxis()

for bar in bars:
    ax.text(bar.get_width() + 10000, bar.get_y() + bar.get_height() / 2, f'{int(bar.get_width()):,}', va='center', ha='left', fontsize=12)

ax.grid(axis='x', linestyle='--', alpha=0.7)
plt.tight_layout()

sm = plt.cm.ScalarMappable(cmap='viridis', norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax)
cbar.set_label('Post Count', rotation=270, labelpad=15)

plt.savefig('top_20_hashtags_colored.png', dpi=300)
plt.show()
