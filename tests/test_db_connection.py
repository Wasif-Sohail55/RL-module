"""Tests for ADO.NET connection string parsing in db.py"""
import pytest
from urllib.parse import unquote_plus

from db import _parse_adonet_connection_string, _build_sqlalchemy_url


class TestParseAdonetConnectionString:
    def test_parse_basic_connection_string(self):
        conn_str = "Server=myserver;Database=mydb;User Id=myuser;Password=mypass;"
        result = _parse_adonet_connection_string(conn_str)
        assert result["Server"] == "myserver"
        assert result["Database"] == "mydb"
        assert result["User Id"] == "myuser"
        assert result["Password"] == "mypass"

    def test_parse_azure_connection_string(self):
        conn_str = (
            'Server=tcp:projectserver2181104.database.windows.net,1433;'
            'Initial Catalog=projectdatabase181104;Encrypt=True;'
            'TrustServerCertificate=False;Connection Timeout=30;'
            'Authentication="Active Directory Default";'
        )
        result = _parse_adonet_connection_string(conn_str)
        assert result["Server"] == "tcp:projectserver2181104.database.windows.net,1433"
        assert result["Initial Catalog"] == "projectdatabase181104"
        assert result["Encrypt"] == "True"
        assert result["TrustServerCertificate"] == "False"
        assert result["Connection Timeout"] == "30"
        assert result["Authentication"] == "Active Directory Default"

    def test_parse_handles_empty_parts(self):
        conn_str = "Server=myserver;;Database=mydb;"
        result = _parse_adonet_connection_string(conn_str)
        assert result["Server"] == "myserver"
        assert result["Database"] == "mydb"
        assert len(result) == 2


class TestBuildSqlalchemyUrl:
    def test_returns_sqlalchemy_url_unchanged(self):
        url = "mssql+pyodbc://user:pass@server/db"
        result = _build_sqlalchemy_url(url)
        assert result == url

    def test_returns_sqlite_url_unchanged(self):
        url = "sqlite+pysqlite:///:memory:"
        result = _build_sqlalchemy_url(url)
        assert result == url

    def test_converts_azure_ad_connection_string(self):
        conn_str = (
            'Server=tcp:projectserver2181104.database.windows.net,1433;'
            'Initial Catalog=projectdatabase181104;Encrypt=True;'
            'TrustServerCertificate=False;Connection Timeout=30;'
            'Authentication="Active Directory Default";'
        )
        result = _build_sqlalchemy_url(conn_str)
        
        # Check the URL structure - uses odbc_connect parameter
        assert result.startswith("mssql+pyodbc:///?odbc_connect=")
        
        # Extract and decode the odbc_connect value
        odbc_connect = result.split("odbc_connect=")[1]
        decoded = unquote_plus(odbc_connect)
        
        # Check ODBC connection string parts
        assert "DRIVER={ODBC Driver 18 for SQL Server}" in decoded
        assert "SERVER=projectserver2181104.database.windows.net,1433" in decoded
        assert "DATABASE=projectdatabase181104" in decoded
        assert "Encrypt=yes" in decoded
        assert "TrustServerCertificate=no" in decoded
        assert "Authentication=ActiveDirectoryDefault" in decoded
        assert "Connection Timeout=30" in decoded

    def test_converts_sql_auth_connection_string(self):
        conn_str = (
            "Server=myserver.database.windows.net,1433;"
            "Initial Catalog=mydb;"
            "User Id=myuser;"
            "Password=myp@ssword;"
        )
        result = _build_sqlalchemy_url(conn_str)
        
        assert result.startswith("mssql+pyodbc:///?odbc_connect=")
        
        # Extract and decode the odbc_connect value
        odbc_connect = result.split("odbc_connect=")[1]
        decoded = unquote_plus(odbc_connect)
        
        assert "UID=myuser" in decoded
        assert "PWD=myp@ssword" in decoded
        assert "SERVER=myserver.database.windows.net,1433" in decoded
        assert "DATABASE=mydb" in decoded

    def test_handles_data_source_alias(self):
        conn_str = "Data Source=myserver;Database=mydb;"
        result = _build_sqlalchemy_url(conn_str)
        
        odbc_connect = result.split("odbc_connect=")[1]
        decoded = unquote_plus(odbc_connect)
        
        assert "SERVER=myserver" in decoded
        assert "DATABASE=mydb" in decoded

    def test_default_driver_when_not_specified(self):
        conn_str = "Server=myserver;Database=mydb;"
        result = _build_sqlalchemy_url(conn_str)
        
        odbc_connect = result.split("odbc_connect=")[1]
        decoded = unquote_plus(odbc_connect)
        
        assert "DRIVER={ODBC Driver 18 for SQL Server}" in decoded

    def test_custom_driver_in_connection_string(self):
        conn_str = "Server=myserver;Database=mydb;Driver=ODBC Driver 17 for SQL Server;"
        result = _build_sqlalchemy_url(conn_str)
        
        odbc_connect = result.split("odbc_connect=")[1]
        decoded = unquote_plus(odbc_connect)
        
        assert "DRIVER={ODBC Driver 17 for SQL Server}" in decoded
        assert "ODBC Driver 18" not in decoded

    def test_custom_driver_with_braces_preserved(self):
        conn_str = "Server=myserver;Database=mydb;Driver={ODBC Driver 17 for SQL Server};"
        result = _build_sqlalchemy_url(conn_str)
        
        odbc_connect = result.split("odbc_connect=")[1]
        decoded = unquote_plus(odbc_connect)
        
        assert "DRIVER={ODBC Driver 17 for SQL Server}" in decoded
