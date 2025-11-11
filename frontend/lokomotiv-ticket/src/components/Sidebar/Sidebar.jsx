import React from 'react';
import './Sidebar.css';
import logoutIcon from '../../assets/images/log-out.png';
import { Link } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';

export const Sidebar = ({ isOpen, onClose }) => {
  const navigate = useNavigate();

  const handleLogout = () => {

    navigate('/');
  };

  return (
    <div className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="closeButton" onClick={onClose}>×</div>
      <div className="menuItems">
        <Link to="/operator">Оператор</Link>
        <Link to="/cashier">Кассир</Link>
        <Link to="/admin">Админ</Link>
      </div>
      <button className="logout" onClick={handleLogout}>
        <span>Выход</span>
        <img src={logoutIcon} alt="Выход" className="logoutIcon" />
      </button>
    </div>
  );
};