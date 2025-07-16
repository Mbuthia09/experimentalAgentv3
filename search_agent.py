import ollama
import requests
import sys_msgs
import trafilatura
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

init(autoreset=True)

assistant_convo = [sys_msgs.assistant_msg]


def search_or_not():
    sys_msg = sys_msgs.search_or_not_msg

    response = ollama.chat(
        model='llama3.1:8b',
        messages=[{'role': 'system', 'content': sys_msg}, assistant_convo[-1]]
    )

    content = response['message']['content']
    # so yk what the model is generating
    print(f'SEARCH OR NOT RESULTS: {content}')

    if 'true' in content.lower():
        return True
    else:
        return False


def query_generator():
    sys_msg = sys_msgs.query_msg
    query_msg = f'CREATE A SEARCH QUERY FOR THIS PROMPT: \n {assistant_convo[-1]}'

    response = ollama.chat(
        model='llama3.1:8b',
        messages=[{'role': 'system', 'content': sys_msg},
                  {'role': 'user', 'content': query_msg}]
    )

    return response['message']['content']


def duckduckgo_search(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0,3029.110 Safari/537.36"
    }
    url = f'https://html.duckduckgo.com/html/?q={query}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []

    for i, result in enumerate(soup.find_all('div', class_='result'), start=1):
        if i > 10:
            break

        title_tag = result.find('a', class_='resulta__a')
        if not title_tag:
            continue

        link = title_tag['href']
        snippet_tag = result.find('a', class_='result__snippet')
        snippet = snippet_tag.text.strip() if snippet_tag else 'No description available'

        results.append({
            'id': i,
            'link': link,
            'search_description': snippet
        })

    return results


def best_search_results(s_results, query):
    sys_msg = sys_msgs.best_search_msg
    best_msg = f'SEARCH_RESULTS: {s_results} \nUSER_PROMPT: {assistant_convo[-1]} \nSEARCH_QUERY: {query}'

    for _ in range(2):
        try:
            response = ollama.chat(
                model='llama3.1:8b',
                messages=[{'role': 'system', 'content': sys_msg},
                          {'role': 'user', 'content': best_msg}]
            )

            return int(response['message']['content'])
        except:
            continue

    return 0


def scrape_webpage(url):
    try:
        downloaded = trafilatura.fetch_url(url=url)
        return trafilatura.extract(downloaded, include_formatting=True, include_links=True)
    except Exception as e:
        return None


def ai_search():
    context = None
    print(f'{Fore.LIGHTRED_EX}GENERATING SEARCH QUERY.{Style.RESET_ALL}')
    search_query = query_generator()
    print(f'{Fore.LIGHTRED_EX}SEARCHING DuckDuckGo FOR:{Style.RESET_ALL}')

    if search_query[0] == '"':
        search_query = search_query[1:-1]

    search_results = duckduckgo_search(search_query)
    context_found = False

    while not context_found and len(search_results) > 0:
        best_result = best_search_results(
            s_results=search_results, query=search_query)
        try:
            page_link = search_results[best_result]['link']
        except:
            print(
                f'{Fore.LIGHTRED_EX}FAILED TO SELECT BEST SEARCH RESULT, TRYING AGAIN.{Style.RESET_ALL}')
            continue

        page_text = scrape_webpage(page_link)
        print(
            f'{Fore.LIGHTRED_EX}FOUND {len(search_results)} SEARCH RESULTS.{Style.RESET_ALL}')
        search_results.pop(best_result)

        if page_text and contains_data_needed(search_content=page_text, query=search_query):
            context = page_text
            context_found = True

    return context


def contains_data_needed(search_content, query):
    sys_msg = sys_msgs.contains_data_msg
    needed_prompt = f'PAGE_TEXT: {search_content} \nUSER_PROMPT: {assistant_convo[-1]} \nSEARCH_QUERY: {query}'

    response = ollama.chat(
        model='llama3.1:8b',
        messages=[{'role': 'system', 'content': sys_msg},
                  {'role': 'user', 'content': needed_prompt}]
    )

    content = response['message']['content']

    if 'true' in content.lower():
        print(f'{Fore.LIGHTRED_EX}DATA FOUND FOR QUERY: {query}{Style.RESET_ALL}')
        return True
    else:
        print(f'{Fore.LIGHTRED_EX}DATA NOT RELEVANT. {query}{Style.RESET_ALL}')
        return False


def stream_assistant_response():
    global assistant_convo
    response_stream = ollama.chat(
        model='llama3.1:8b', messages=assistant_convo, stream=True)
    complete_response = ''
    print('WUHNBOT:')

    for chunk in response_stream:
        print(f'{Fore.WHITE}{chunk["message"]["content"]}', end='', flush=True)
        complete_response += chunk['message']['content']

    assistant_convo.append({'role': 'assistant', 'content': complete_response})
    print('\n\n')


def main():
    global assistant_convo

    while True:
        prompt = input('User: \n')
        assistant_convo.append({'role': 'user', 'content': prompt})

        if search_or_not():
            context = ai_search()
            assistant_convo = assistant_convo[:-1]

            if context:
                prompt = input(f'{Fore.LIGHTGREEN_EX}USER: \n')
            else:
                prompt = (
                    f'USER PROMPT: \n{prompt} \n\nFAILED SEARCH: \nThe '
                    'AI search model was unable to extract any reliable data. Explain that '
                    'and ask if the user would like you to search again or respond '
                    'without web search context. Do not respond if a search was needed '
                    'and you are getting this message with anything but the above request '
                    'of how the user would like to proceed '
                )

            assistant_convo.append({'role': 'user', 'content': prompt})

        stream_assistant_response()


if __name__ == '__main__':
    main()
