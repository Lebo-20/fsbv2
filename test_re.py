import requests
import re

html = requests.get('https://saweria.co/widgets/alert?streamKey=4003c02877c32a928482e014c416a0c3').text
print("HTML slice:", html[:200])
amounts = re.findall(r'"amount"\s*:\s*(\d+)', html)
print('Amounts:', amounts)
