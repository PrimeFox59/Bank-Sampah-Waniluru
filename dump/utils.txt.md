import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime, timedelta

def get_all_categories():
    """Get all waste categories"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_category_by_id(category_id):
    """Get category by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()
    conn.close()
    return category

def create_category(name, price_per_kg):
    """Create a new category"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO categories (name, price_per_kg)
            VALUES (?, ?)
        ''', (name, price_per_kg))
        conn.commit()
        conn.close()
        return True, "Kategori berhasil ditambahkan"
    except Exception as e:
        conn.close()
        return False, str(e)

def update_category_price(category_id, new_price):
    """Update category price"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE categories 
        SET price_per_kg = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_price, category_id))
    conn.commit()
    conn.close()

def delete_category(category_id):
    """Delete a category"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        conn.commit()
        conn.close()
        return True, "Kategori berhasil dihapus"
    except Exception as e:
        conn.close()
        return False, str(e)

def create_transaction(warga_id, category_id, weight_kg, processed_by, notes="", batch_id="", transaction_date=None):
    """Create a new transaction (supports batch_id for multi-item grouping and custom date)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get category price
    cursor.execute('SELECT price_per_kg FROM categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()
    price_per_kg = category[0]
    
    # Calculate amounts
    total_amount = weight_kg * price_per_kg
    committee_fee = total_amount * 0.10  # 10% for committee
    net_amount = total_amount - committee_fee
    
    # Get current balance
    cursor.execute('SELECT balance FROM users WHERE id = ?', (warga_id,))
    current_balance = cursor.fetchone()[0]
    
    # Insert transaction
    if transaction_date is None:
        transaction_date = datetime.now()

    cursor.execute('''
                INSERT INTO transactions 
                (warga_id, category_id, weight_kg, price_per_kg, total_amount, 
                 committee_fee, net_amount, processed_by, batch_id, notes, transaction_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (warga_id, category_id, weight_kg, price_per_kg, total_amount,
                    committee_fee, net_amount, processed_by, batch_id, notes, transaction_date))
    
    transaction_id = cursor.lastrowid
    
    # Update warga balance
    new_balance = current_balance + net_amount
    cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, warga_id))
    
    # Record committee earnings
    cursor.execute('''
        INSERT INTO committee_earnings (transaction_id, amount)
        VALUES (?, ?)
    ''', (transaction_id, committee_fee))
    
    conn.commit()
    conn.close()
    
    return True, transaction_id, {
        'total_amount': total_amount,
        'committee_fee': committee_fee,
        'net_amount': net_amount,
        'new_balance': new_balance
    }

def get_user_balance(user_id):
    """Get user balance"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
    balance = cursor.fetchone()[0]
    conn.close()
    return balance

def process_withdrawal(warga_id, amount, processed_by, notes=""):
    """Process a withdrawal"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get current balance
    cursor.execute('SELECT balance FROM users WHERE id = ?', (warga_id,))
    current_balance = cursor.fetchone()[0]
    
    if current_balance < amount:
        conn.close()
        return False, "Saldo tidak mencukupi"
    
    new_balance = current_balance - amount
    
    # Insert financial movement
    cursor.execute('''
        INSERT INTO financial_movements 
        (warga_id, type, amount, balance_before, balance_after, processed_by, notes)
        VALUES (?, 'withdrawal', ?, ?, ?, ?, ?)
    ''', (warga_id, amount, current_balance, new_balance, processed_by, notes))
    
    # Update balance
    cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, warga_id))
    
    conn.commit()
    conn.close()
    
    return True, new_balance

def process_deposit(warga_id, amount, processed_by, notes=""):
    """Process a deposit"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get current balance
    cursor.execute('SELECT balance FROM users WHERE id = ?', (warga_id,))
    current_balance = cursor.fetchone()[0]
    
    new_balance = current_balance + amount
    
    # Insert financial movement
    cursor.execute('''
        INSERT INTO financial_movements 
        (warga_id, type, amount, balance_before, balance_after, processed_by, notes)
        VALUES (?, 'deposit', ?, ?, ?, ?, ?)
    ''', (warga_id, amount, current_balance, new_balance, processed_by, notes))
    
    # Update balance
    cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, warga_id))
    
    conn.commit()
    conn.close()
    
    return True, new_balance

def get_transactions(warga_id=None, limit=None, start_date=None, end_date=None):
    """Get transactions with optional filters"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT t.*, u.full_name as warga_name, c.name as category_name,
               p.full_name as processed_by_name
        FROM transactions t
        JOIN users u ON t.warga_id = u.id
        JOIN categories c ON t.category_id = c.id
        JOIN users p ON t.processed_by = p.id
        WHERE 1=1
    '''
    params = []
    
    if warga_id:
        query += ' AND t.warga_id = ?'
        params.append(warga_id)
    
    if start_date:
        query += ' AND DATE(t.transaction_date) >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND DATE(t.transaction_date) <= ?'
        params.append(end_date)
    
    query += ' ORDER BY t.transaction_date DESC'
    
    if limit:
        query += f' LIMIT {limit}'
    
    cursor.execute(query, params)
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def get_financial_movements(warga_id=None, limit=None):
    """Get financial movements"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT fm.*, u.full_name as warga_name, p.full_name as processed_by_name
        FROM financial_movements fm
        JOIN users u ON fm.warga_id = u.id
        JOIN users p ON fm.processed_by = p.id
        WHERE 1=1
    '''
    params = []
    
    if warga_id:
        query += ' AND fm.warga_id = ?'
        params.append(warga_id)
    
    query += ' ORDER BY fm.movement_date DESC'
    
    if limit:
        query += f' LIMIT {limit}'
    
    cursor.execute(query, params)
    movements = cursor.fetchall()
    conn.close()
    return movements

def get_committee_total_earnings(start_date=None, end_date=None):
    """Get total committee earnings"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT SUM(amount) FROM committee_earnings WHERE 1=1'
    params = []
    
    if start_date:
        query += ' AND DATE(earned_date) >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND DATE(earned_date) <= ?'
        params.append(end_date)
    
    cursor.execute(query, params)
    total = cursor.fetchone()[0] or 0
    conn.close()
    return total

def get_monthly_statistics(year, month):
    """Get monthly statistics"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total transactions
    cursor.execute('''
        SELECT COUNT(*), SUM(total_amount), SUM(weight_kg)
        FROM transactions
        WHERE strftime('%Y', transaction_date) = ? 
        AND strftime('%m', transaction_date) = ?
    ''', (str(year), str(month).zfill(2)))
    
    stats = cursor.fetchone()
    
    result = {
        'total_transactions': stats[0] or 0,
        'total_revenue': stats[1] or 0,
        'total_weight': stats[2] or 0
    }
    
    conn.close()
    return result

def get_yearly_statistics(year):
    """Get yearly statistics"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*), SUM(total_amount), SUM(weight_kg)
        FROM transactions
        WHERE strftime('%Y', transaction_date) = ?
    ''', (str(year),))
    
    stats = cursor.fetchone()
    
    result = {
        'total_transactions': stats[0] or 0,
        'total_revenue': stats[1] or 0,
        'total_weight': stats[2] or 0
    }
    
    conn.close()
    return result

def get_warga_performance(warga_id, start_date=None, end_date=None):
    """Get warga performance statistics"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT COUNT(*) as total_transactions,
               SUM(weight_kg) as total_weight,
               SUM(total_amount) as total_revenue,
               SUM(net_amount) as total_earned
        FROM transactions
        WHERE warga_id = ?
    '''
    params = [warga_id]
    
    if start_date:
        query += ' AND DATE(transaction_date) >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND DATE(transaction_date) <= ?'
        params.append(end_date)
    
    cursor.execute(query, params)
    stats = cursor.fetchone()
    
    conn.close()
    
    return {
        'total_transactions': stats[0] or 0,
        'total_weight': stats[1] or 0,
        'total_revenue': stats[2] or 0,
        'total_earned': stats[3] or 0
    }

def get_audit_logs(user_id=None, limit=100):
    """Get audit logs"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT al.*, u.username, u.full_name, u.role
        FROM audit_log al
        JOIN users u ON al.user_id = u.id
        WHERE 1=1
    '''
    params = []
    
    if user_id:
        query += ' AND al.user_id = ?'
        params.append(user_id)
    
    query += ' ORDER BY al.timestamp DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    logs = cursor.fetchall()
    conn.close()
    return logs

def is_input_period_active():
    """Check if transaction input is currently allowed for inputer role"""
    from database import get_setting
    import json
    
    # 1. Check mode
    mode = get_setting('input_availability_mode', 'manual')
    
    if mode == 'manual':
        status = get_setting('input_manual_status', '1')
        return status == '1'
        
    elif mode == 'scheduled':
        config_json = get_setting('input_schedule_config', '{}')
        try:
            config = json.loads(config_json)
        except:
            return False # Fail safe
            
        now = datetime.now()
        
        # Check time window first (applies to all days)
        if 'time_start' in config and 'time_end' in config:
            current_time = now.strftime('%H:%M')
            if not (config['time_start'] <= current_time <= config['time_end']):
                return False

        # Check weekly schedule (Days of week)
        # 0=Monday, 6=Sunday
        if 'weekly' in config and config['weekly']:
            # Config stores day names in English or index? Let's use English names for clarity in JSON
            # Monday, Tuesday, etc.
            day_name = now.strftime('%A')
            if day_name not in config['weekly']:
                return False
                
        # Check monthly schedule (Dates)
        if 'monthly' in config and config['monthly']:
            # List of integers [1, 2, ..., 31]
            if now.day not in config['monthly']:
                return False
                
        # If we passed all checks (or checks were empty/permissive)
        return True
        
    return False
