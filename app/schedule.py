import asyncio
import common
import os




if __name__ == '__main__':
    for k, v in os.environ.items():
        print(type(k), k, v)
    x = os.environ.get('VERIFY_SLL', 'False') == 'True'
    print(f'{x=}', type(x))
    # asyncio.run(common.queryWorkpackages())