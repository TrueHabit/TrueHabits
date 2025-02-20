# OK

import openai

def separar_acciones(texto):
    # Esta funcion llama a ChatGPT para analizar el texto y separar las acciones encontradas
    prompt = f"""
Dado un texto del usuario separa las acciones que se mencionan en el texto y devuelvelas separadas por '~~'.

EN EL TEXTO PUEDE HABER:
1) UNA sola accion.
2) MULTIPLES acciones, en la misma oracion o en distintas oraciones.
3) Distintas referencias temporales (por ejemplo: "ayer", "hoy", "el fin de semana pasado", "por la noche", etc.).
   Si se menciona algun termino temporal, anadelo a todas las acciones que correspondan a ese periodo temporal.

MUESTRA LAS SIGUIENTES SITUACIONES A TRAVES DE LOS EJEMPLOS:

EJEMPLO 1 (una sola accion):
Hoy me levante.
-> Hoy me levante

EJEMPLO 2 (dos acciones en la misma oracion):
Hoy he salido a correr 10 km y me he bebido 3 vasos de agua
-> Hoy he salido a correr 10 km ~~ Hoy me he bebido 3 vasos de agua

EJEMPLO 3 (varias acciones con distintas referencias temporales):
Ayer me bebi una fanta y hoy por la manana he corrido y jugado al futbol
-> Ayer me bebi una fanta ~~ hoy por la manana he corrido ~~ hoy por la manana he jugado al futbol

EJEMPLO 4 (terminos temporales con oraciones separadas):
El fin de semana pasado sali con mis amigos. Despues vi una pelicula y cene sushi
-> El fin de semana pasado sali con mis amigos ~~ El fin de semana pasado vi una pelicula ~~ El fin de semana pasado cene sushi

INSTRUCCIONES PARA LA SALIDA:
- Devuelve UNICAMENTE el texto de entrada troceado, sin anadir nada mas excepto el contexto temporal en caso de que sea necesario.
- NO incluyas contexto adicional, solo las acciones separadas por el separador '~~'.

TEXTO DEL USUARIO:
"{texto}"
    """

    # Se utiliza un bloque try-except para manejar posibles errores de llamada a la API
    try:
        # Se realiza la llamada a la API de ChatGPT para separar las acciones
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente util que analiza texto y devuelve un texto con las diferentes acciones separadas por el separador '~~'."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.0,
        )
        # Se obtiene la respuesta y se limpia el contenido
        contenido = response.choices[0].message.content.strip()
        # Se separan las acciones usando el delimitador '~~' y se eliminan espacios extra
        contenido = [elemento.strip() for elemento in contenido.split("~~")]
        # Se retorna la lista de acciones separadas
        return contenido

    except Exception as e:
        # En caso de error, se devuelve un mensaje de error
        return f"Ha ocurrido un error: {e}"
