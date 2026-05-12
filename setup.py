from setuptools import setup, find_packages

setup(
    name="travel_with_maki", # Теперь проект официально называется так
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "flask",
    ],
    entry_points={
        "console_scripts": [
            "run-travel-app=travel_app.app:main",
        ],
    },
)