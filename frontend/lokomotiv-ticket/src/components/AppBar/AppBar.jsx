import React from 'react';
import './AppBar.css';
import logo from '../../assets/images/example-logo.png';
import menuIcon from '../../assets/images/menu.png';

export const AppBar = ({ pageTitle, onMenuClick }) => {
  return (
    <div className="appBar">
      <div className="leftSection">
        <div className="logoContainer">
          <img src={logo} alt="Лого" className="logoImage" />
        </div>
        <span className="pageTitle">{pageTitle}</span>
      </div>

      <button className="menuButton" onClick={onMenuClick}>
        <img src={menuIcon} alt="Меню" className="menuImage" />
      </button>
    </div>
  );
};
