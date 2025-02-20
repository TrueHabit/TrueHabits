# OK
# objetivos.py

import openai
from BBDD_create.database import Habito
from config import OPENAI_API_KEY

def get_objetivo_mensaje(session, user_id: int, texto_input, habito: str, valor_logrado: float, habito_obj) -> str:
    """
    Esta funcion obtiene el objetivo de un habito y genera un mensaje motivacional usando ChatGPT
    """

    # Se verifica si existe el objeto de habito y su objetivo
    if not habito_obj or not habito_obj.objetivo:
        return ""

    # Se extrae el texto del objetivo y se comprueba si esta vacio
    objetivo_texto = habito_obj.objetivo.strip()
    if not objetivo_texto:
        return ""

    # Se construye el prompt con la informacion necesaria
    prompt = f"""
Eres un asistente que redacta mensajes breves de motivacion o felicitacion basados en preguntas del usuario, en su desempeno real y en su objetivo.

Contexto:
- El mensaje es una pregunta numerica o textual sobre algo relacionado con los habitos (por ejemplo: "cuantas veces he corrido en los ultimos 3 dias").
- El usuario tiene un objetivo concreto (por ejemplo: "Fumar menos de 2 cigarrillos al dia", "Beber 2 litros de agua diarios", "Correr 10 km a la semana", etc.).
- En el período consultado, el usuario ha logrado una cierta cantidad (esta cifra o texto indica la media o el total de lo que hizo).
- Debes:
  1. Interpretar la pregunta y responder en funcion del valor que se te da.
  2. Compararla con el valor del objetivo.
  3. Decidir si el objetivo se cumplio, se supero o todavia no se alcanzo.
  4. Redactar un mensaje breve y positivo en espanol, de animo o felicitacion. 
    - El mensaje debe reflejar cuanto ha realizado el usuario.
    - El mensaje debe decir cual es el objetivo.
    - El mensaje debe reflejar lo realizado por el usuario y el objetivo.
    - Comprueba si se ha cumplido el objetivo, si estas seguro de los calculos dale un mensaje de felicitacion si se ha cumplido el objetivo y uno de animo si no. (IMPORTANTE) Si no tienes claro si lo ha cumplido el objetivo no digas si lo ha hecho, solo dale animos y la otra informacion requerida.
    - Ten en cuenta la frecuencia del objetivo y extrapola eso en caso de que se te solicite mas informacion.
    - No incluyas pasos de tu razonamiento en el mensaje final. Solo responde con el texto para el usuario.


Ejemplo 1:
Pregunta: ¿Cuántos kilómetros he corrido esta semana?
Hábito: Correr
Valor logrado por usuario: 12 km
Objetivo del hábito: Correr al menos 10 km a la semana
Cantidad objetivo: 10 km
Frecuencia objetivo: Semanal

Respuesta: ¡🏃‍♂️💪 Increíble trabajo! Esta semana corriste 12 km, superando tu objetivo de 10 km semanales. Sigue así, ¡estás alcanzando tus metas con determinación! 🎉🔥

Ejemplo 2:
Pregunta: ¿Cuántos cigarrillos he fumado hoy?
Hábito: Fumar
Valor logrado por usuario: 1 cigarrillo
Objetivo del hábito: Fumar menos de 2 cigarrillos al día
Cantidad objetivo: 2 cigarrillo
Frecuencia objetivo: Diaria

Respuesta: 🎉 ¡Felicidades! Hoy fumaste solo 1 cigarrillo, cumpliendo tu objetivo de fumar menos de 2 al día. 🚭 Cada día estás logrando un progreso impresionante. ¡Sigue así! 👏🌟

Ejemplo 3:
Pregunta: ¿Cuántos vasos de agua he bebido en los últimos 3 días?
Hábito: Beber agua
Valor logrado por usuario: 4 vasos
Objetivo del hábito: Beber al menos 2 litros de agua diarios (8 vasos)
Cantidad objetivo: 8 vasos
Frecuencia objetivo: Diaria

Respuesta: 💧 ¡Buen esfuerzo! En los últimos 3 días bebiste un promedio de 4 vasos de agua diarios. Aunque aún no alcanzas tu objetivo de 8 vasos al día, estás dando pasos importantes. 🚀 ¡Continúa esforzándote, lo lograrás pronto! 🌟💙

Ejemplo 4:
Pregunta: ¿Cuántas veces hice ejercicio esta semana?
Hábito: Ejercicio
Valor logrado por usuario: 3 días
Objetivo del hábito: Hacer ejercicio al menos 5 días a la semana
Cantidad objetivo: 5 días
Frecuencia objetivo: Semanal

Respuesta: 🏋️‍♀️ ¡Vas por buen camino! Esta semana hiciste ejercicio 3 días. Aunque aún faltan 2 días para alcanzar tu meta de 5 días semanales, estás avanzando. 💪 ¡No te rindas, puedes lograrlo! 🚀👏

Ejemplo 5: (ejemplo en el que no esta claro si ha cumplido o no el objetivo)
Pregunta: ¿Cuántos vasos de agua he bebido en el último mes?
Hábito: Beber agua
Valor logrado por usuario: 70 vasos
Objetivo del hábito: Beber al menos 2 litros de agua diarios (8 vasos)
Cantidad objetivo: 8 vasos
Frecuencia objetivo: Diaria

Respuesta:  💧 ¡Impresionante! En los últimos días has bebido un total de 19.0 Litros de agua. ¡Estás hidratándote de manera excepcional! Sigue así, cuidando tu cuerpo con este hábito tan saludable y tu objetivo de 5 Litros diarios. ¡Excelente trabajo! 💦👏

Ejemplo 6:
Pregunta: ¿Cuántas horas he dormido por noche en promedio esta semana?
Hábito: Dormir
Valor logrado por usuario: 32 horas
Objetivo del hábito: Dormir al menos 7 horas por noche
Cantidad objetivo: 7 horas
Frecuencia objetivo: Diaria

Respuesta: 😴 ¡Buen intento! Esta semana dormiste un promedio de 6 horas por noche. Aunque no llegaste a las 7 horas diarias que te propusiste, cada mejora cuenta. 🌟 ¡Prioriza tu descanso, vas en la dirección correcta! 🌙✨

* (IMPORTANTE) recuerda que si sabes si se ha cumplido el objetivo no digas que lo haya hecho.
* (IMPORTANTE) no copies los ejemplos, se original

Ahora, con la información del usuario :
Pregunta: {texto_input}
Habito: {habito}
Valor logrado por usuario: {valor_logrado} {habito_obj.unidad_medida_objetivo}
Objetivo del habito: {habito_obj.objetivo}
Cantidad objetivo: {habito_obj.cantidad_objetivo} {habito_obj.unidad_medida_objetivo}
Frencuencia objetivo: {habito_obj.frecuencia_objetivo}
"""

    try:
        # Se hace la llamada a la API de ChatGPT para generar el mensaje
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente que redacta mensajes motivacionales breves y positivos, "
                        "en funcion de un objetivo y el progreso del usuario. Pero tienes que tener cuidado de si no sabes algo"
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_tokens=150,
        )
        # Se obtiene el contenido del mensaje generado
        mensaje = response.choices[0].message.content.strip()
        return mensaje
    except Exception as e:
        # Se captura cualquier error y se muestra
        print(f"[ERROR ChatGPT Objetivos] {e}")
        return ""
