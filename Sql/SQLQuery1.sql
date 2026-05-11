CREATE DATABASE Golden_StateDB

CREATE SCHEMA Golden

CREATE LOGIN Isaac WITH PASSWORD = 'admin123';
CREATE LOGIN Harold WITH PASSWORD = 'admin123';
CREATE LOGIN Marcos WITH PASSWORD = 'admin123';
CREATE LOGIN Lisbeth WITH PASSWORD = 'admin123';
CREATE LOGIN Efrain WITH PASSWORD = 'admin123';



CREATE USER Isaac FOR LOGIN Isaac;
CREATE USER Harold FOR LOGIN Harold;
CREATE USER Marcos FOR LOGIN Marcos;
CREATE USER Lisbeth FOR LOGIN Lisbeth;
CREATE USER Efrain FOR LOGIN Efrain;



ALTER SERVER ROLE sysadmin ADD MEMBER Isaac;
ALTER SERVER ROLE sysadmin ADD MEMBER Harold;
ALTER SERVER ROLE sysadmin ADD MEMBER Marcos;
ALTER SERVER ROLE sysadmin ADD MEMBER Lisbeth;
ALTER SERVER ROLE sysadmin ADD MEMBER Efrain;

Create table 

CREATE TABLE Golden.Contrato (
        ID_Contrato int NOT NULL PRIMARY KEY IDENTITY(1,1),
        ID_Jugador int,
        Fecha_Inicio_Contrato date,
        Fecha_Fin_Contrato date,
        Valor_Total decimal,
        Equipos_Contratantes int,
        Cláusulas_Especiales nvarchar(max)
    );

ALTER TABLE Golden.Contrato
ADD CONSTRAINT FK_Contrato_Jugador FOREIGN KEY (ID_Jugador)
REFERENCES Golden.Jugadores(ID_Jugador)

ALTER TABLE Golden.Contrato
ADD CONSTRAINT FK_Contrato_Equipo FOREIGN KEY (Equipos_Contratantes)
REFERENCES Golden.Equipo(ID_Equipo)



CREATE TABLE Golden.Equipo (
        ID_Equipo int NOT NULL PRIMARY KEY IDENTITY(1,1),
        Nombre_Equipo nvarchar(max)
    );


    CREATE TABLE Golden.Jugadores (
        ID_Jugador int NOT NULL PRIMARY KEY IDENTITY(1,1),
        Nombre nvarchar(max),
        Apellido nvarchar(max),
        Fecha_Nacimiento date,
        Posicion nvarchar(max),
        Altura decimal,
        Peso decimal,
        Nacionalidad nvarchar(max),
        Estado nvarchar(max)
    );


CREATE TABLE Golden.Jugadores_Temporadas (
        ID_Jugador_Temporada int NOT NULL PRIMARY KEY IDENTITY(1,1),
        ID_Jugador int,
        ID_Temporada int,
        Minutos_Jugados int,
        Puntos_Por_Juego decimal,
        Asistencias_Por_Juego decimal,
        Rebotes_Ofensivos decimal,
        Rebotes_Defensivos decimal,
        Robos_Por_Juego decimal,
        Tapones_Por_Juego decimal,
        Juegos_Jugados int,
        Faltas_Juegos bigint
    );

	ALTER TABLE Golden.Jugadores_Temporadas
	ADD CONSTRAINT FK_Jugadores_Temporada_Jugador FOREIGN KEY (ID_Jugador)
	REFERENCES Golden.Jugadores(ID_Jugador)

	ALTER TABLE Golden.Jugadores_Temporadas
	ADD CONSTRAINT FK_ID_Temporada_Temporada FOREIGN KEY (ID_Temporada)
	REFERENCES Golden.Temporada(ID_Temporada)


    CREATE TABLE Golden.Salario (
        ID_Salario int NOT NULL PRIMARY KEY IDENTITY(1,1),
        ID_Jugador int,
        ID_Temporada int,
        Salario_Base decimal,
        Bonos decimal,
        Fecha_Pago date,
        Total_Salario decimal
    );
		
	ALTER TABLE Golden.Salario
	ADD CONSTRAINT FK_Salario_Jugador FOREIGN KEY (ID_Jugador)
	REFERENCES Golden.Jugadores(ID_Jugador)

	ALTER TABLE Golden.Salario
	ADD CONSTRAINT FK_Salario_Temporada FOREIGN KEY (ID_Temporada)
	REFERENCES Golden.Temporada(ID_Temporada)

    CREATE TABLE Golden.Temporada (
        ID_Temporada int NOT NULL PRIMARY KEY IDENTITY(1,1),
        Año_Inicio int,
        Año_Fin int
    );


	select * from dbo.Temporada
	select * from Golden.Temporada

SET IDENTITY_INSERT Golden.Temporada ON;

INSERT INTO Golden.Temporada (ID_Temporada, Año_Inicio, Año_Fin)
SELECT ID_Temporada, Año_Inicio, Año_Fin
FROM dbo.Temporada;

SET IDENTITY_INSERT Golden.Temporada OFF;
