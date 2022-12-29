## Install APP
    sudo apt-get update
    sudo apt install python3
	sudo apt install virtualenv
    sudo apt install ffmpeg
    virtualenv venv --python=python3

    make config.json file from the sample inside the project folder
    source project_folder/venv/bin/activate
    pip install -r requirements.txt

## Cron settings
    0 */2 * * * /home/ubuntu/project_folder/venv/bin/python /home/ubuntu/project_folder/cron.py

## Install chrome + chromedriver
    sudo nano /etc/apt/sources.list.d/google-chrome.list
    deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main
    wget https://dl.google.com/linux/linux_signing_key.pub
    sudo apt-key add linux_signing_key.pub
    sudo apt update
    sudo apt install google-chrome-stable

At the end you just need to download chromedriver !!!

## RUN APP
    nohup project_path/venv/bin/python project_path/app.py > /dev/null &