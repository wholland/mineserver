from setuptools import setup, find_packages

setup(  name='mineserver',
        version='1.0',
        description='Management script for minecraft server',
        author='Wes Holland',
        author_email='whatswithwes@gmail.com',
        license='MIT',
        packages=find_packages(),
        install_requires=[
            'Click',
            'libtmux'
        ],
        entry_points='''
            [console_scripts]
            mineserver=mineserver.mineserver:cli
        ''')

