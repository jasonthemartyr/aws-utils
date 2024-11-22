import json
import asyncio
# from cost_utils.ip_utils import 

async def main():
    config = load_config()
    data = await async_config_query(config.get('AGGREGATOR_NAME'), config.get('CONFIG_QUERIES'))

    if config.get('PRINT'):
        pretty_print_data = json.dumps(data, indent=4)
        print(pretty_print_data)
    if config.get('SAVE_FILE'):
        file = config.get('SAVE_FILE_NAME')
        with open(file, 'w', encoding='utf-8') as f: # type: ignore
            json.dump(data, f, ensure_ascii=False, indent=4)
    if config.get('SEARCH_IP'):
        matches = search_for_ip(data, config.get('SEARCH_IP'))
        if matches:
            print(f'match found for {config.get('SEARCH_IP')}')
            for match in matches:
                print(json.dumps(match, indent=4))
        else:
            print(f'no matches found for {config.get('SEARCH_IP')}')

if __name__=="__main__":
    asyncio.run(main())