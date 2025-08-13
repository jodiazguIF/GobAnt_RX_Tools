from ia_handling import *
from drive_implementations import *
from sheets_modifications import *
from rutinas import *
import time

'''En este archivo main va a correr la aplicación encargada de gestionar la interacción entre la IA,
Google Drive y Google Sheets. El objetivo principal es el siguiente:

1. Ayudar continuamente al usuario en su tarea de mantener la base de datos
 
Por lo tanto se quiere que la IA realice las siguientes rutinas:
- Monitorear la aparición o no de nuevos archivos en Google Drive.
- Actualizar automáticamente los datos en Google Sheets cuando se detecten cambios.
- Proporcionar resúmenes periódicos de la información almacenada en Google Sheets.

Todo esto con el fin de liberar muchas tareas repetitivas del usuario
'''



while (1):
    monitorear_drive()
