from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class Passenger(Base):
    __tablename__ = 'passenger'
    RFIDNo = Column(Integer, primary_key=True, nullable=False)
    Balance = Column(Integer, nullable=False)
    def __repr__(self):
        return f"<Passenger(RFIDNo={self.RFIDNo}, Balance={self.Balance})>"

class Routes(Base):
    __tablename__ = 'routes'
    RouteNo = Column(String(10), primary_key=True, nullable=False)
    SOURCE = Column(String(20), nullable=False)
    DESTINATION = Column(String(20), nullable=True)
    def __repr__(self):
        return f"<Routes(RouteNo='{self.RouteNo}', SOURCE='{self.SOURCE}', DESTINATION='{self.DESTINATION}')>"

class Stations(Base):
    __tablename__ = 'stations'
    RouteNo = Column(String(10), ForeignKey('routes.RouteNo'), nullable=True, index=True)  # Assuming a 'routes' table exists
    STATION_NUMBER = Column(Integer, nullable=True)
    STATION_NAME = Column(String(100), nullable=True)
    def __repr__(self):
        return f"<Station(RouteNo='{self.RouteNo}', STATION_NUMBER={self.STATION_NUMBER}, STATION_NAME='{self.STATION_NAME}')>"

class Ticket(Base):
    __tablename__ = 'ticket'
    TICKETID = Column(Integer, primary_key=True, autoincrement=True)
    TIMESTAMP = Column(DateTime, default=func.current_timestamp(), nullable=True)
    START_STOP = Column(Integer, nullable=True)
    END_STOP = Column(Integer, nullable=True)
    RFID_NO = Column(Integer, ForeignKey('passenger.RFIDNo'), nullable=True)
    ROUTENO = Column(String(10), ForeignKey('routes.RouteNo'), nullable=True)
    def __repr__(self):
        return (f"<Ticket(TICKETID={self.TICKETID}, TIMESTAMP={self.TIMESTAMP}, "
                f"START_STOP={self.START_STOP}, END_STOP={self.END_STOP}, "
                f"RFID_NO={self.RFID_NO}, ROUTENO={self.ROUTENO})>")

class Fare(Base):
    __tablename__ = 'fare'
    RouteNo = Column(String(10), ForeignKey('routes.RouteNo'), nullable=True, index=True)
    Station1 = Column(String(100), nullable=False)
    Station2 = Column(String(100), nullable=True)
    Fare = Column(Integer, nullable=True)
    def __repr__(self):
        return (f"<Fare(RouteNo='{self.RouteNo}', Station1='{self.Station1}', "
                f"Station2='{self.Station2}', Fare={self.Fare})>")

class Recharge(Base):
    __tablename__ = 'recharge'
    RFIDNo = Column(Integer, ForeignKey('passenger.RFIDNo'), nullable=True)
    RechargeDate = Column(DateTime, server_default=func.current_timestamp(), nullable=True)
    RechargeAmount = Column(Integer, nullable=True) 
    def __repr__(self):
        return f"<Recharge(RFIDNo={self.RFIDNo}, RechargeDate={self.RechargeDate}, RechargeAmount={self.RechargeAmount})>"

class Register(Base):
    __tablename__ = 'register' 
    username = Column(String(20), primary_key=True, nullable=False)
    password = Column(String(1000), nullable=True)
    def __repr__(self):
        return f"<Register(username='{self.username}')>"