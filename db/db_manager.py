from sqlalchemy import create_engine, Column, Date, DateTime, Boolean, MetaData, Table, String, Integer, inspect, insert, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import Union, List, Dict
from utils.config import get_postgres_url

from datetime import datetime

# Define the base class for your table models
Base = declarative_base()

# Define the timetable table
class Timetable(Base):
    __tablename__ = 'timetable'
    start = Column(Date, primary_key=True)  # Assuming 'start' is a unique field, hence primary key
    end = Column(Date)
    completed = Column(Boolean)

class Tokenpairstable(Base):
    __tablename__ = 'token_pairs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    token0 = Column(String, nullable=False)
    token1 = Column(String, nullable=False)
    fee = Column(Integer, nullable=False)
    pool = Column(String, nullable=False)
    block_number = Column(Integer, nullable=False)
    completed = Column(Boolean, nullable=False)

class Pooldatatable(Base):
    __tablename__ = 'pool_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    block_number = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)
    transaction_hash = Column(String, nullable=False)

class SwapEventTable(Base):
    __tablename__ = 'swap_event'
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_hash = Column(String, nullable=False)
    pool_address = Column(String, nullable=False)
    block_number = Column(Integer, nullable=False)
    sender = Column(String, nullable=False)
    to = Column(String, nullable=False)
    amount0 = Column(String, nullable=False)  # I256 can be stored as String
    amount1 = Column(String, nullable=False)  # I256 can be stored as String
    sqrt_price_x96 = Column(String, nullable=False)  # U256 can be stored as String
    liquidity = Column(String, nullable=False)  # U256 can be stored as String
    tick = Column(Integer, nullable=False)  # i32 can be stored as Integer

class MintEventTable(Base):
    __tablename__ = 'mint_event'
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_hash = Column(String, nullable=False)
    pool_address = Column(String, nullable=False)
    block_number = Column(Integer, nullable=False)
    sender = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    tick_lower = Column(Integer, nullable=False)  # int24 can be stored as Integer
    tick_upper = Column(Integer, nullable=False)  # int24 can be stored as Integer
    amount = Column(String, nullable=False)  # U256 can be stored as String
    amount0 = Column(String, nullable=False)  # U256 can be stored as String
    amount1 = Column(String, nullable=False)  # U256 can be stored as String

class BurnEventTable(Base):
    __tablename__ = 'burn_event'
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_hash = Column(String, nullable=False)
    pool_address = Column(String, nullable=False)
    block_number = Column(Integer, nullable=False)
    owner = Column(String, nullable=False)
    tick_lower = Column(Integer, nullable=False)  # int24 can be stored as Integer
    tick_upper = Column(Integer, nullable=False)  # int24 can be stored as Integer
    amount = Column(String, nullable=False)  # U256 can be stored as String
    amount0 = Column(String, nullable=False)  # U256 can be stored as String
    amount1 = Column(String, nullable=False)  # U256 can be stored as String

class CollectEventTable(Base):
    __tablename__ = 'collect_event'
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_hash = Column(String, nullable=False)
    pool_address = Column(String, nullable=False)
    block_number = Column(Integer, nullable=False)
    owner = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    tick_lower = Column(Integer, nullable=False)  # int24 can be stored as Integer
    tick_upper = Column(Integer, nullable=False)  # int24 can be stored as Integer
    amount0 = Column(String, nullable=False)  # U256 can be stored as String
    amount1 = Column(String, nullable=False)  # U256 can be stored as String

class UniswapSignalsTable(Base):
    __tablename__ = 'uniswap_signals'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    pool_address = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    liquidity = Column(Integer, nullable=False)
    volume = Column(Integer, nullable=False)

class DBManager:

    def __init__(self, url = get_postgres_url()) -> None:
        # Create the SQLAlchemy engine
        self.engine = create_engine(url)

        # Create a configured "Session" class
        self.Session = sessionmaker(bind=self.engine)

        # Create the table if it doesn't exist
        Base.metadata.create_all(self.engine)  # This line ensures the table is created if not exists

        # Enable TimescaleDB and convert specific tables to hypertables
        self.create_hypertables()

    def create_hypertables(self):
        """Enable TimescaleDB extension and convert tables to hypertables."""
        with self.engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            try:
                # Check if TimescaleDB extension is already installed
                result = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb';"))
                if not result.fetchone():
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                    print("TimescaleDB extension created successfully.")
                else:
                    print("TimescaleDB extension already exists.")

                # Check if hypertable is enabled
                result = conn.execute(text(
                    "SELECT * FROM timescaledb_information.hypertables;"
                )).fetchall()
                hypertables = [entry.hypertable_name for entry in result]
                
                tables = ['timetable', 'pool_data', 'token_pairs', 'swap_event', 'mint_event', 'burn_event', 'collect_event']
                for table in tables:
                    if table not in hypertables:
                        conn.execute(text(
                            f"SELECT create_hypertable('{table}', 'id', if_not_exists => TRUE, migrate_data => true);"
                        ))
                        print(f"Hypertable '{table}' created successfully.")
                    else:
                        print(f"Hypertable '{table}' already exists.")
                conn.execute(text(
                    f"""
                    SELECT create_hypertable(
                        'uniswap_signals', 
                        'timestamp', 
                        if_not_exists => TRUE, 
                        migrate_data => true, 
                        chunk_time_interval => INTERVAL '1 day'
                    );
                    """
                ))

            except SQLAlchemyError as e:
                print(f"An error occurred: {e}")
        
    def __enter__(self):
        self.session = self.Session()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Don't forget to close the session
        self.session.close()
    
    def add_timetable_entry(self, start: Date, end: Date) -> None:
        """Add a new timetable entry to the database."""
        with self.Session() as session:
            new_entry = Timetable(start=start, end=end, completed=False)
            session.add(new_entry)
            session.commit()

    def fetch_timetable_data(self) -> List[Dict[str, Union[Date, bool]]]:
        """Fetch all timetable data from the database."""
        with self.Session() as session:
            timetable_data = session.query(Timetable).all()
            return [{"start": row.start, "end": row.end, "completed": row.completed} for row in timetable_data]

    def fetch_incompleted_time_range(self) -> List[Dict[str, Union[Date, bool]]]:
        """Fetch all not completed time ranges from the timetable."""
        with self.Session() as session:
            not_completed_data = session.query(Timetable).filter_by(completed=False).all()
            return [{"start": row.start, "end": row.end, "completed": row.completed} for row in not_completed_data]
    
    def fetch_last_time_range(self) -> Dict[str, Union[datetime, bool]]:
        """Fetch the last time range from the timetable."""
        with self.Session() as session:
            last_time_range = session.query(Timetable).order_by(Timetable.start.desc()).first()
            if last_time_range is not None:
                return {"start": datetime.combine(last_time_range.start, datetime.min.time()), 
                        "end": datetime.combine(last_time_range.end, datetime.min.time()), 
                        "completed": last_time_range.completed}
            else:
                return None

    def mark_time_range_as_complete(self, start: Date, end: Date) -> bool:
        """Mark a timetable entry as complete."""
        with self.Session() as session:
            record = session.query(Timetable).filter_by(start=start, end=end).first()
            if record:
                record.completed = True
                session.commit()
                return True
            return False

    def add_token_pairs(self, token_pairs: List[Dict[str, Union[str, int]]]) -> None:
        """Add token pairs to the corresponding table."""
        
        insert_values = [
            Tokenpairstable(token0 = token_pair['token0'], token1 = token_pair['token1'], fee = token_pair['fee'], pool = token_pair['pool'], block_number = token_pair['block_number'], completed = False)
            for token_pair in token_pairs
        ]
        
        with self.Session() as session:
            session.add_all(insert_values)
            session.commit()
    
    def fetch_token_pairs(self):
        """Fetch all token pairs from the corresponding table."""
        with self.Session() as session:
            token_pairs = session.query(Tokenpairstable).all()
            return [{"token0": row.token0, "token1": row.token1, "fee": row.fee, "completed": row.completed} for row in token_pairs]

    def fetch_incompleted_token_pairs(self) -> List[Dict[str, Union[str, int, bool]]]:
        """Fetch all incompleted token pairs from the corresponding table."""
        with self.Session() as session:
            incompleted_token_pairs = session.query(Tokenpairstable).filter_by(completed=False).all()
            return [{"token0": row.token0, "token1": row.token1, "fee": row.fee, "completed": row.completed} for row in incompleted_token_pairs]

    def mark_token_pairs_as_complete(self, token_pairs: List[tuple]) -> bool:
        """Mark a token pair as complete."""
        with self.Session() as session:
            for token_pair in token_pairs:
                record = session.query(Tokenpairstable).filter_by(token0=token_pair[0], token1=token_pair[1], fee=token_pair[2]).first()
                if record:
                    session.query(Tokenpairstable).filter_by(token0=token_pair[0], token1=token_pair[1], fee=token_pair[2]).update({Tokenpairstable.completed: True})
                else:
                    return False
            session.commit()
            return True
    def reset_token_pairs(self):
        """Reset the token pairs completed state"""
        with self.Session() as session:
            session.query(Tokenpairstable).update({Tokenpairstable.completed: False})
            session.commit()

    def add_pool_data(self, pool_data: List[Dict]) -> None:
        """Add pool data to the pool data table and related event tables."""
        insert_values = [
            Pooldatatable(block_number=data['block_number'], event_type=data['event']['type'], transaction_hash=data['transaction_hash'])
            for data in pool_data
        ]

        with self.Session() as session:
            session.add_all(insert_values)  # Add the pool data to the pool data table
            session.commit()

        # Add the swap event data to the swap event table
        swap_event_data = [
            SwapEventTable(transaction_hash=data['transaction_hash'], pool_address = data['pool_address'], block_number=data['block_number'], **data['event']['data'])
            for data in pool_data if data['event']['type'] == 'swap'
        ]
        if swap_event_data:
            with self.Session() as session:
                session.add_all(swap_event_data)
                session.commit()

        # Add the mint event data to the mint event table
        mint_event_data = [
            MintEventTable(transaction_hash=data['transaction_hash'], pool_address = data['pool_address'], block_number=data['block_number'], **data['event']['data'])
            for data in pool_data if data['event']['type'] == 'mint'
        ]
        if mint_event_data:
            with self.Session() as session:
                session.add_all(mint_event_data)
                session.commit()

        # Add the burn event data to the burn event table
        burn_event_data = [
            BurnEventTable(transaction_hash=data['transaction_hash'], pool_address = data['pool_address'], block_number=data['block_number'], **data['event']['data'])
            for data in pool_data if data['event']['type'] == 'burn'
        ]
        if burn_event_data:
            with self.Session() as session:
                session.add_all(burn_event_data)
                session.commit()

        # Add the collect event data to the collect event table
        collect_event_data = [
            CollectEventTable(transaction_hash=data['transaction_hash'], pool_address = data['pool_address'], block_number=data['block_number'], **data['event']['data'])
            for data in pool_data if data['event']['type'] == 'collect'
        ]
        if collect_event_data:
            with self.Session() as session:
                session.add_all(collect_event_data)
                session.commit()
    
    def add_uniswap_signals(self, signals: List[Dict]) -> None:
        """Add Uniswap signals to the corresponding table."""
        insert_values = [
            UniswapSignalsTable(timestamp=signal['timestamp'], pool_address=signal['pool_address'], price=signal['price'], liquidity=signal['liquidity'], volume=signal['volume'])
            for signal in signals
        ]

        with self.Session() as session:
            session.add_all(insert_values)
            session.commit()
