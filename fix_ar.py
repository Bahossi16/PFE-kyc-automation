import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', database='cbs_kyc', charset='utf8mb4')
cursor = conn.cursor()
cursor.execute("UPDATE clients SET nom_ar = 'سويبقي', prenom_ar = 'دليلة' WHERE cin = '12621583'")
cursor.execute("UPDATE clients SET nom_ar = 'بنعمار', prenom_ar = 'وصال' WHERE cin = '13511348'")
conn.commit()
print('Noms arabes mis a jour !')
