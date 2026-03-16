git init
python -m venv venv
source venv/Scripts/activate
python.exe -m pip install --upgrade pip

pip install -r requirements.txt
pip install confluent-kafka
pip install mysql-connector-python
pip install elasticsearch
pip install pydantic

pip freeze > requirements.txt
git add .  
git commit -m "initial commit"
git push -u origin main

branches
git checkout -b intel
git checkout -b attack
git checkout -b damage

