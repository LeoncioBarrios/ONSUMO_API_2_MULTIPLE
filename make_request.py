from flask import Flask
from flask_mail import Mail
from datetime import datetime

from conexion_db import Conexion, ConexionMutual

import logging
from smtplib import SMTPException
from threading import Thread
from flask_mail import Message

import json
import schedule
import time
import os
import requests   # Producción.
import re

from modelo import DBCredentials

#-- Diccionario para registrar las cuentas con errores para ser notificadas y las veces
#-- que se ha notificado: {nro_cta: n_veces}
ctas_errores_informadas = dict()
#-- Dict para controlar el reinicio de todas las notificaciones por el tiempo programadao con MINUTOS_CTRL: {mutual: True}
notificar_todo = dict()

#-- Cargar las variables de entorno. ---------------------------------------------------------------------------------
SECRET_KEY = os.getenv('SECRET_KEY')

EMAIL_SERVER = os.getenv('EMAIL_SERVER')
EMAIL_PORT = int(os.getenv('EMAIL_PORT'))
EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

SEGUNDOS_CTRL = int(os.getenv('SEGUNDOS_CTRL'))   # Frecuencia de envío de correos de notificación. (Segundos)
MINUTOS_CTRL = int(os.getenv('MINUTOS_CTRL'))     # Frecuencia de reinicio de envío de correos de todas las notificaciones. (Minutos)

#---------------------------------------------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# Creación de la aplicación con Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

#-- Configuración correo.
app.config['MAIL_SERVER'] = EMAIL_SERVER
app.config['MAIL_PORT'] = EMAIL_PORT
app.config['MAIL_USERNAME'] = EMAIL_USERNAME
app.config['MAIL_PASSWORD'] = EMAIL_PASSWORD
app.config['MAIL_USE_TLS'] = True

mail = Mail(app)
#----------------------------------------------------------------------------------------------------
def write_log(message):
	if not os.path.exists("logs"):
		os.makedirs("logs")
	
	with open(f"logs/{DBCredentials.CUIT}.txt", "a", encoding="utf-8") as file:
		file.write(message)


def _send_async_email(app, msg):
	with app.app_context():
		try:
			mail.send(msg)
		except SMTPException:
			logger.exception("Ocurrió un error al enviar el email")


def send_email(subject, sender, recipients, text_body, cc=None, bcc=None, html_body=None):
	msg = Message(subject, sender=sender, recipients=recipients, cc=cc, bcc=bcc)
	msg.body = text_body
	if html_body:
		msg.html = html_body
	Thread(target=_send_async_email, args=(app, msg)).start()


def correo(subject=None, body=None):
	if not subject:
		subject = EMAIL_SUBJECT   # Asunto.
	sender = EMAIL_SENDER         # Correo remitente.
	
	if DBCredentials.EMAIL_RECIPIENTS:
		correos = re.split(r'[,; ]+', DBCredentials.EMAIL_RECIPIENTS)
		correos = [correo.strip() for correo in correos if correo.strip()]
		
	else:
		correos = []
	
	recipients = correos
	
	text_body = None
	html_body = body
	
	if DBCredentials.EMAIL_ENVIO_CC:
		correos = re.split(r'[,; ]+', DBCredentials.EMAIL_ENVIO_CC)
		correos = [correo.strip() for correo in correos if correo.strip()]
		
	else:
		correos = []
	
	cc = correos
	bcc = None
	
	send_email(subject, sender, recipients, text_body, cc=cc, bcc=bcc, html_body=html_body)


def search_datos():
	datos = None
	try:
		with ConexionMutual.get_connection() as conexion:
			with conexion.cursor() as cursor:
				cursor.execute("SELECT * FROM AMVSaldos WHERE modificado = 1")
				datos = cursor.fetchall() 
	
	except Exception as e:
		detail="No se pudo establecer la conexión con el servidor!!!"
		print(detail, e)
	
	return datos


def get_mutuales():
	try:
		with Conexion.get_connection() as conexion:
			with conexion.cursor() as cursor:
				cursor.execute("SELECT * FROM Mutuales WHERE Activo = 1")
				mutuales = cursor.fetchall()
	
	except Exception as e:
		detail="No se pudo establecer la conexión con el servidor!!!"
		print(detail, e)
	
	return mutuales


def verificar_saldos():
	mutuales = get_mutuales()
	
	for mutual in mutuales:
		DBCredentials.CUIT = mutual[1]
		DBCredentials.MUTUAL = mutual[2]
		DBCredentials.DATA_BASE = mutual[3]
		DBCredentials.USER_DB = mutual[4]
		DBCredentials.PASS_DB = mutual[5]
		DBCredentials.EMAIL_RECIPIENTS = mutual[6]
		DBCredentials.EMAIL_ENVIO_CC = mutual[7]
		DBCredentials.USUARIO_SERVICIO_BICA = mutual[10]
		DBCredentials.PASSWORD_SERVICIO_BICA = mutual[11]
		DBCredentials.CONVENIO = mutual[12]
		DBCredentials.URL_SERVICIO_BICA = mutual[13]
		
		make_request()


def make_request():
	print("******")
	print("Ejecutó la función make_request")
	global notificar_todo
	
	cuentas_actualizadas = search_datos()
	
	if cuentas_actualizadas:
		__URL = DBCredentials.URL_SERVICIO_BICA
		__USUARIO = DBCredentials.USUARIO_SERVICIO_BICA
		__PASSWORD = DBCredentials.PASSWORD_SERVICIO_BICA

		headers = {
			'Accept': 'application/json',
			'Content-Type': 'application/json; charset=UTF-8'
		}
		
		# Creación de la lista de diccionarios de saldos informados
		SaldosInformados = []
		for fila in cuentas_actualizadas:
			# crear el diccionario
			dictsaldos = {
				"CuentaMutual": fila[0],
				"Saldo": float(fila[1]),
				"FechaHoraSaldo": str(fila[2].date())+" "+
								str(fila[2].hour)+":"+str(fila[2].minute)+":"+str(fila[2].second)
			}
			SaldosInformados.append(dictsaldos)
		
		# Creación del diccionario de envío de saldos de la mutual
		SaldoMutual = {
			"SaldoMutual": {
				"CantidadRegistros": len(SaldosInformados),
				"Convenio": DBCredentials.CONVENIO,
				"SaldosInformados": SaldosInformados
			}
		}
		
		body = SaldoMutual

		try:
			
			# Realizar la solicitud POST al endpoint con los encabezados, la autenticación y el cuerpo del mensaje
			response = json.loads(local_response())  # Para pruebas locales (simular request).          # Para DESARROLLO!!
			#response = requests.post(__URL, headers=headers, auth=(__USUARIO, __PASSWORD), json=body)   # Para PRODUCCIÓN!!
			
			if response["status_code"] == 200:   # Para DESARROLLO!!
			#if response.status_code == 200:      # Para PRODUCCIÓN!!
				
				respuesta = response["contenido"]   # Para DESARROLLO!!
				#respuesta = response.json()         # Para PRODUCCIÓN!!
				
				# Crear lista de Cuentas SaldosInformados
				ListaCuentasInformadas = []
				for elemento1 in SaldosInformados:
					ListaCuentasInformadas.append(elemento1['CuentaMutual'])
				
				# Crear lista de Cuentas ErroresSaldos
				ListaErroresSaldos = []
				for elemento1 in respuesta["InformarSaldosResult"]["ErroresSaldos"]:
					ListaErroresSaldos.append(elemento1['CuentaMutual'])
				
				# Crear lista de cuentas para cambio de estado en la tabla
				ListaActualizarEstados = list(filter(lambda cta: cta not in ListaErroresSaldos, ListaCuentasInformadas))
				
				# Actualizar en la Base de Datos
				# Implementar el procedimiento almacenado
				
				if ListaActualizarEstados:
					try:
						with ConexionMutual.get_connection() as conexion:
							with conexion.cursor() as cursor:
								for cuenta in ListaActualizarEstados:
									comandoSQL ="exec dbo.SaldoMovimiento @icuenta=?, @bmodificado=?"
									param = (cuenta, False)
									cursor.execute(comandoSQL, param)
									conexion.commit()
					
					except Exception as e:
						lin1 = "<h3>No se pudo establecer la conexión con el servidor!!!!</h3>"
						lin2 = f"<p>{e}</p>"
						body = lin1 + lin2
						correo(body=body)
				
				if ListaErroresSaldos:
					#-- Flag para determinar si hay que notificar cuando haya algo nuevo por notificar.
					notif = False
					
					for cta in ListaErroresSaldos:
						#-- Comprobar si existe algo nuevo por notificar, si es cierto, se procederá a notificar todo.
						
						#-- Comprobar si existe la mutual en el dict de control.
						if DBCredentials.CUIT not in ctas_errores_informadas:
							ctas_errores_informadas.update({DBCredentials.CUIT: {}})
							notif = True
							
							#-- Agregar la mutual para ctrl notificar_todo.
							notificar_todo.update({DBCredentials.CUIT: True})
							
							break
						
						else:
							#-- Comprobar la cuenta de la mutual en el dict de control.
							if cta not in ctas_errores_informadas[DBCredentials.CUIT]:
								notif = True
								break
					
					#-- Si hay algo nuevo por notificar o si ya ha pasado el tiempo (MINUTOS_CTRL) para volver a notificar todo lo ya notificado de haber.
					if notif or notificar_todo[DBCredentials.CUIT]:
						#-- Preparar el cuero del correo para su envío.
						intro1 = f"<p>Cantidad de Registros Procesado: <strong>{respuesta['InformarSaldosResult']['CantidadRegistrosProcesados']}</strong></p>"
						intro2 = f"<p>Cantidad de Registros Incorrectos: <strong>{respuesta['InformarSaldosResult']['CantidadRegistrosIncorrectos']}</strong></p>"
						
						p1 = """
								<table>
									<thead>
										<tr>
											<th style='width: 14%; text-align: left; border: 1px solid black;'>Cuenta Mutual</th>
											<th style='width: 50%; text-align: left;border: 1px solid black;'>Descripción Error</th>
											<th style='width: 14%; text-align: left;border: 1px solid black;'>Fecha/Hora Saldo</th>
											<th style='width: 12%; text-align: right;border: 1px solid black;'>Saldo</th>
											<th style='width: 10%; text-align: right;border: 1px solid black;'>Veces notificada</th>
										</tr>
									</thead>
								<tbody>"""
						
						p3 = "</tbody></table>"
						
						p2 = ""
						
						for cta in respuesta["InformarSaldosResult"]["ErroresSaldos"]:
							#-- Comprobar si existe la mutual en el dict de control.
							if cta['CuentaMutual'] not in ctas_errores_informadas[DBCredentials.CUIT]:
								#-- Si se está notificando por primera vez, se agrega al dict de control y la cant. de veces es 1.
								ctas_errores_informadas[DBCredentials.CUIT].update({cta['CuentaMutual']:1})
								
							else:
								#-- Si ya había sido notificada, se actualiza la cantidad de veces.
								ctas_errores_informadas[DBCredentials.CUIT][cta['CuentaMutual']] +=1
							
							p2 = p2 + f"""
							<tr>
								<td style='vertical-align: top;'>{cta['CuentaMutual']}</td>
								<td style='vertical-align: top;'>{cta['DetalleError']}</td>
								<td style='vertical-align: top;'>{cta['FechaHoraSaldo']}</td>
								<td style='vertical-align: top; text-align: right;'>{cta['Saldo']}</td>
								<td style='vertical-align: top; text-align: right;'>{ctas_errores_informadas[DBCredentials.CUIT][cta['CuentaMutual']]}</td>
							</tr>"""
						
						#-- Se ensambla el cuerpo del mensaje del correo.
						body = intro1 + intro2 + p1 + p2 + p3
						
						#-- Se invoca a la función para que se configure el correo y su envío.
						correo(body=body)
						#-- Se establece el flag para que se vulva a notificar todo lo que hay por notificar en el tiempo programado con MINUTOS_CTRL.
						notificar_todo[DBCredentials.CUIT] = False
					else:
						#-- Quitar las ctas. que se han corregido del dict. de control.
						copia = ctas_errores_informadas[DBCredentials.CUIT].copy()
						
						for cta in copia:
							if cta not in ListaErroresSaldos:
								#-- Si la cta. fue corregida, eliminar de control.
								ctas_errores_informadas[DBCredentials.CUIT].pop(cta)
							
						del copia
					
					#-- Escribir en el log los saldos notificados sin problemas:
					if ListaActualizarEstados:
						message = f"{datetime.today()} | Saldos notificados. | Cuentas sin problemas: {ListaActualizarEstados} | Cuentas con problemas: {ListaErroresSaldos}\n"
						write_log(message)
				
				else:
					#-- Si no se reportan ctas. con errores es porque se solucionaron, por lo tanto se debe blanquear el dict. de control.
					if DBCredentials.CUIT in ctas_errores_informadas:
						ctas_errores_informadas.pop(DBCredentials.CUIT)
					
					#-- Escribir en el log todo satisfactoriamente procesado:
					message = f"{datetime.today()} | Todos los saldos notificados sin problemas. | Cuentas: {ListaActualizarEstados}\n"
					write_log(message)
				
			else:
				lin1 = "<h3>Error en la solicitud</h3>"
				lin2 = f"<h4>status code: {response.status_code}</h4>"
				body = lin1 + lin2
				
				correo(body=body)
		
		except Exception as e:
			print("Ha ocurrido un error con la conexión al servicio", e)
			subject = "Fallo servicio BICA (Informar Saldos)"
			lin1 = "<h3>Ha ocurrido un error con el servicio BICA para informar los Saldos</h3>"
			lin2 = f"<p>{e}</p>"
			body = lin1 + lin2
			
			correo(subject=subject, body=body)


def reset_notificar_todo():
	#-- Establecer flag en cada mutual para que se pueda notificar todas las novedades:
	#-- tanto las ya notificadas como las nuevas si las hay.
	global notificar_todo
	for mutual in notificar_todo:
		notificar_todo[mutual] = True


#-- Función para pruebas locales.
def local_response():
	# if DBCredentials.DATA_BASE == 'PruebaBICAMutual':
	if DBCredentials.DATA_BASE == 'BICAMutual':
		archivo = 'datos_bica.json'
	else:
		archivo = 'datos_otra.json'
	
	with open(archivo) as archivo:
		datos = json.load(archivo)
	
	resp = json.dumps(datos)
	return resp


#-- Después de cada minutos indicados en la variable MINUTOS_CTRL, se llama a la función make_request()
#schedule.every(SEGUNDOS_CTRL).seconds.do(verificar_saldos)   # Para PRODUCCIÓN.
schedule.every(2).seconds.do(verificar_saldos)              # Para pruebas locales.

#-- Transcurridas cada horas indicadas en la variable HORAS_CTRL, se llama a la función notificar_todo()
#schedule.every(MINUTOS_CTRL).minutes.do(reset_notificar_todo)   # Para PRODUCCIÓN.
schedule.every(20).seconds.do(reset_notificar_todo)            # Para pruebas locales.

# Bucle para que la tarea de programación
# Siga funcionando todo el tiempo.

#-- El bucle while se utiliza para verificar y ejecutar las tareas programadas en intervalos regulares. 
#-- schedule.run_pending() verifica si alguna tarea programada debe ejecutarse y time.sleep(1) evita 
#-- que el programa consuma demasiada CPU mientras espera.
while True:
	schedule.run_pending()
	time.sleep(1)




# ListaCuentasInformadas = [1000026, 1000133, 1000747]
# ListaErroresSaldos = [1000026, 1000747]
# ListaActualizarEstados = [1000133]
 
