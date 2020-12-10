from flask import Flask, json, request
from pymongo import MongoClient


USER = "grupo9"
PASS = "grupo9"
DATABASE = "grupo9"

URL = f"mongodb://{USER}:{PASS}@gray.ing.puc.cl/{DATABASE}?authSource=admin"
client = MongoClient(URL)

USER_KEYS = ['uid', 'name', 'age', 'description']

MSG_KEYS = ['message', 'sender', 'receptant',
            'lat', 'long', 'date']

TEXT_SEARCH_KEYS = ['desired', 'required', 'forbidden', 'userId']

# Base de datos del grupo
db = client["grupo9"]

# Seleccionamos la collección de usuarios
usuarios = db.usuarios
mensajes = db.mensajes

#Iniciamos la aplicación de flask
app = Flask(__name__)

#Error handler 
def no_mid(mid):
    return json.jsonify({
        "ErrorCode": 418,
        "ErrorDetail": f"mid {mid} not found"
    })

def no_uid(uid):
    return json.jsonify({
        "ErrorCode": 419,
        "ErrorDetail": f"uid {uid} not found"
    })

def no_post_body():
    return json.jsonify({
        "ErrorCode": 420,
        "ErrorDetail": f"body not found"
    })


def no_post_param(key):
    return json.jsonify({
        "ErrorCode": 421,
        "ErrorDetail": f"key {key} not found"
    })
    
@app.errorhandler(404)
def invalid_route(e):
    return json.jsonify({
        "ErrorCode": 404,
        "ErrorDetail": "Page not found, enter valid mid"
        })

@app.errorhandler(400)
def no_body(e):
    return get_messages()


#Página de inicio
@app.route("/", methods=["GET"])
def home():
    '''
    Página de inicio
    '''
    return "<h1>¡Hola!</h1>"

######### USERS ###########
@app.route("/users")
def get_users():
    '''
    Obtiene todos los usuarios
    '''
    users = list(usuarios.find({}, {"_id": 0}))
    return json.jsonify(users)

@app.route("/users/<int:uid>")
def get_user(uid):
    '''
    Obtiene el usuario de id entregado
    '''
    user = list(usuarios.find({"uid": uid}, {"_id": 0}))
    if len(user) == 0:
        return no_uid(uid)

    user[0]["mesagges_sended"] = list(mensajes.find({"sender": uid}, {"_id": 0}))

    return json.jsonify(user)

######### MESSAGES ##########
@app.route("/messages")
def get_messages():
    '''
    Obtiene todos los mensajes o mensaje entre 2 personas
    '''
    id1 = request.args.get("id1", False)
    id2 = request.args.get("id2", False)

    if not id1 or not id2:
        messages = list(mensajes.find({}, {"_id": 0}))

    else:
        id_1 = list(usuarios.find({"uid": int(id1)}, {"_id": 0}))
        id_2 = list(usuarios.find({"uid": int(id2)}, {"_id": 0}))
        if len(id_1) == 0:
            return no_uid(id1)
        elif len(id_2) == 0:
            return no_uid(id2)

        messages = list(mensajes.find({
            "$or": [
                {"$and": [
                    {"sender": int(id1)},
                    {"receptant": int(id2)}]
                },
                {"$and": [
                    {"sender": int(id2)},
                    {"receptant": int(id1)}]   
                }
            ]
        }, {"_id": 0}))


    return json.jsonify(messages)

@app.route("/messages/<int:mid>")
def get_message(mid):
    '''
    Obtiene el mensaje de id entregado
    '''
    message = list(mensajes.find({"mid": mid}, {"_id": 0}))

    if len(message) == 0:
        return no_mid(mid)

    return json.jsonify(message)



###### METODOS EJEMPLOS DE LA AYUDANTIA ##########
@app.route("/messages", methods=['POST'])
def create_msg():
    '''
    Crea un nuevo usuario en la base de datos
    Se  necesitan todos los atributos de model, a excepcion de _id
    '''
    body = request.get_json(silent=True)
    if body is None:
        return no_post_body()
    data = {}
    for key in MSG_KEYS:
        if key in request.json.keys():
            data[key] = request.json[key]
        else:
            return no_post_param(key)

    # El valor de result nos puede ayudar a revisar
    # si el usuario fue insertado con éxito
    max_id = list(mensajes.find().sort([("mid", -1)]).limit(1))
    data["mid"] = (max_id[0]["mid"] + 1)
    result = mensajes.insert_one(data)

    return json.jsonify({"success": True})

###### METODO DELETE ###########

@app.route("/message/<int:mid>", methods=['DELETE'])
def delete_msg(mid):
    '''
    Elimina el msg de id entregada
    '''
    message = list(mensajes.find({"mid": mid}, {"_id": 0}))
    if len(message) == 0:
        return no_mid(mid)

    mensajes.remove({"mid": mid})

    return json.jsonify({"success": True})


###### METODO TEXT - SEARCH #######

@app.route("/text-search")
def text_search():
    try:
        request.json
    except ValueError:
        return get_messages()
    if len(request.json) == 0:
        return get_messages()

    data = {key: request.json[key] for key in TEXT_SEARCH_KEYS if key in request.json.keys()}
    search = ''
    sender_review = {}

    only_forbidden = None
    for key in data.keys():
        if key == "required":
            for require in data[key]:
                search += f'"{require}" '
                only_forbidden = False
        elif key == "forbidden":
            for forbidden in data[key]:
                search += f'-{forbidden} '
                if only_forbidden is None:
                    only_forbidden = True
        elif key == "desired":
            for desire in data[key]:
                search += f'{desire} '
                only_forbidden = False
        else:
            user = list(usuarios.find({"uid": data[key]}, {"_id": 0}))
            if len(user) == 0:
                return no_uid(uid)
            sender_review["sender"] = data[key]

    if len(search) > 0:
        search = search[:-1]
    elif len(search) == 0 and "userId" not in data.keys():
        return get_messages()
    
    else:
        message = list(mensajes.find({"sender": sender_review["sender"]}, {"_id": 0}))

        return json.jsonify(message)
    
    mensajes.create_index(name= "indexNone", keys=[("message", "text")], default_language= 'none')

    
    if not only_forbidden:
        filter_msg = mensajes.find({
            "$and": [
                {'$text': {"$search": search}},
                sender_review
            ]
        }, {'score': {'$meta': 'textScore'}, "_id": 0})
        msg_f = list(filter_msg.sort([('score', {'$meta': 'textScore'})]))
    
    else:
        search = search.replace("-", "").replace(" ","|")
        filter_msg = mensajes.find({
            "$and": [
                {'message': {"$not": {"$regex": search, "$options": "si"}}},
                sender_review
            ]
        }, {'score': {'$meta': 'textScore'}, "_id": 0})
        msg_f = list(filter_msg.sort([('score', {'$meta': 'textScore'})]))
    
    return json.jsonify(msg_f)
    

if __name__ == "__main__":
    app.run(debug=True, port= 5000)