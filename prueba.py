""" 
cadena = "leonciobarriosh@gmail.com,  leonciobarriosh@yahoo.com, leonciobarriosh@hotmail.com "

correos = cadena.split(",")

correos = [correo.strip() for correo in correos]
print(correos)
"""

""" 
import re

cadena = "leonciobarriosh@gmail.com;  leonciobarriosh@yahoo.com, leonciobarriosh@hotmail.com castillo@hotmail.com "
cadena = None

if cadena:
	correos = re.split(r'[,; ]+', cadena)
	correos = [correo.strip() for correo in correos if correo.strip()]
else:
	correos = []

cadena = correos

print(correos)
"""


'''
mutuales = [206, 222]
ctas_errores_informadas = {206:{}}


ctas_erradas_206 = [1027, 1047, 1047]
ctas_erradas_222 = [2055]

for mutual in mutuales:
	
	#-- Comprobar para saber si hay qué notificar.
	c = 1047
	if mutual not in ctas_errores_informadas:
		print(f"La cuenta {c} no se encuentra en el dict (1)")
		notif = True
	else:
		if c not in ctas_errores_informadas[mutual]:
			print(f"La cuenta {c} no se encuentra en el dict (2)")
			notif = True
	
	
	#-- Comprobar si existe la mutual en ctrl.
	if mutual not in ctas_errores_informadas:
		ctas_errores_informadas.update({mutual:{}})
	
	#-- Comprobar si existe la cuenta en ctrl.
	ctas_inf_mutual = ctas_errores_informadas[mutual]
	if mutual == 206:
		for cta in ctas_erradas_206:
			if cta in ctas_inf_mutual:
				ctas_inf_mutual[cta] += 1
			else:
				ctas_inf_mutual.update({cta: 1})
		
		#ctas_inf_mutual.clear()
		#ctas_errores_informadas.pop(mutual)
		
	elif mutual == 222:
		for cta in ctas_erradas_222:
			if cta in ctas_inf_mutual:
				ctas_inf_mutual[cta] += 1
			else:
				ctas_inf_mutual.update({cta: 1})
""" 	
	c = 1027
	if c in ctas_errores_informadas[mutual]:
		print(f"Si está en la mutual: {mutual}")
	else:
		print(f"No está en la mutual: {mutual}")
 """	

print(f'El resultado final es: {ctas_errores_informadas}')
'''

""" 
ListaErroresSaldos = [1026, 1047]

ListaCuentasInformadas = [1026, 1033, 1047]

ListaActualizarEstados = list(filter(lambda cta: cta not in ListaErroresSaldos, ListaCuentasInformadas))

print(ListaActualizarEstados)

 """

d1 = "Leoncio"
d2 = "Barrios"
d3 = "Hernández"

cadena = (f"Priemera linea {d1} \
		Segunda linea {d2} \
		Tercera linea {d3}\n".replace('\t', "").strip())


print(cadena)
