from flask import Flask, request, jsonify
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
import os


# Configuracion de la app y DB

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True))
Base = declarative_base()

def get_db():
    """Provee una sesión por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Modelo

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(120), nullable=False, unique=True)  # ejemplo nombre unico
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)


# App Flask

from contextlib import contextmanager
@contextmanager
def session_scope():
    """Context manager para manejar commit/rollback limpios."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

app = Flask(__name__)

#  GET - obtener datos basico
@app.route('/saludo', methods=['GET'])
def saludo():
    return "¡Hola desde Flask!"

#  POST - crear un nuevo recurso 
@app.route('/usuarios', methods=['POST'])
def crear_usuario():
    if not request.is_json:
        return jsonify({"error": "Content-Type debe ser application/json"}), 415

    datos = request.get_json() or {}
    nombre = (datos.get('nombre') or "").strip()

    if not nombre:
        return jsonify({"error": "El campo 'nombre' es requerido"}), 400

    try:
        with session_scope() as db:
            # Validar duplicado 
            existente = db.query(User).filter(User.nombre == nombre).first()
            if existente:
                return jsonify({"error": f"Ya existe un usuario con nombre '{nombre}'"}), 409

            user = User(nombre=nombre)
            db.add(user)
            db.flush()  # para obtener el id asignado

            return jsonify({
                "id": user.id,
                "nombre": user.nombre,
                "created_at": user.created_at.isoformat() + "Z",
                "mensaje": f"Usuario {user.nombre} creado correctamente"
            }), 201
    except Exception as e:
        return jsonify({"error": f"Error al crear usuario: {str(e)}"}), 500

#  PUT - actualizar un recurso
@app.route('/usuarios/<int:id>', methods=['PUT'])
def actualizar_usuario(id):
    if not request.is_json:
        return jsonify({"error": "Content-Type debe ser application/json"}), 415

    datos = request.get_json() or {}
    nuevo_nombre = (datos.get('nombre') or "").strip()
    if not nuevo_nombre:
        return jsonify({"error": "El campo 'nombre' es requerido"}), 400

    try:
        with session_scope() as db:
            user = db.query(User).get(id)
            if not user:
                return jsonify({"error": f"Usuario {id} no encontrado"}), 404

            # Chequear conflicto por unique nombre (si cambia)
            if nuevo_nombre != user.nombre:
                conflicto = db.query(User).filter(User.nombre == nuevo_nombre).first()
                if conflicto:
                    return jsonify({"error": f"Ya existe un usuario con nombre '{nuevo_nombre}'"}), 409

            user.nombre = nuevo_nombre
            db.flush()

            return jsonify({
                "id": user.id,
                "nombre": user.nombre,
                "created_at": user.created_at.isoformat() + "Z",
                "mensaje": f"Usuario {id} actualizado a {nuevo_nombre}"
            }), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar usuario: {str(e)}"}), 500

#  DELETE - eliminar un recurso
@app.route('/usuarios/<int:id>', methods=['DELETE'])
def eliminar_usuario(id):
    try:
        with session_scope() as db:
            user = db.query(User).get(id)
            if not user:
                return jsonify({"error": f"Usuario {id} no encontrado"}), 404

            db.delete(user)
            return jsonify({"mensaje": f"Usuario {id} eliminado"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar usuario: {str(e)}"}), 500

# GET - listar usuarios 
@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 10)), 1), 100)

        with session_scope() as db:
            q = db.query(User).order_by(User.id.asc())
            total = q.count()
            items = q.offset((page - 1) * per_page).limit(per_page).all()

            data = [
    {
        "id": u.id,
        "nombre": u.nombre,
        "created_at": u.created_at.isoformat() + "Z"
    }
    for u in items
]
            return jsonify({
                "page": page,
                "per_page": per_page,
                "total": total,
                "items": data
            }), 200
    except Exception as e:
        return jsonify({"error": f"Error al listar usuarios: {str(e)}"}), 500

# GET - obtener un usuario por id
@app.route('/usuarios/<int:id>', methods=['GET'])
def obtener_usuario(id):
    try:
        with session_scope() as db:
            user = db.query(User).get(id)
            if not user:
                return jsonify({"error": f"Usuario {id} no encontrado"}), 404

            return jsonify({
                "id": user.id,
                "nombre": user.nombre,
                "created_at": user.created_at.isoformat() + "Z"
            }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener usuario: {str(e)}"}), 500

# Ejecutar el servidor
if __name__ == '__main__':
    app.run(debug=True)
