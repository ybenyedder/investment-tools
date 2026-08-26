'use client';

import React, { createContext, useContext, useState } from 'react';

const translations = {
  fr: {
    dashboard: "Tableau de Bord d'Analyse d'Investissement",
    myPortfolio: "💼 Mon Portefeuille",
    logout: "Déconnexion",
    login: "🔐 Se connecter / S'enregistrer",
    optimizeBtn: "⚡ Optimiser (Auto)",
    refresh: "↻ Actualiser",
    reset: "Réinitialiser",
    totalValue: "Valeur totale",
    invested: "Investi",
    cash: "Cash",
    positions: "Positions",
    projection: "Projection 5 ans",
    advice: "Conseils",
    history: "Historique",
    buy: "Acheter",
    sell: "Vendre",
    loading: "Chargement...",
    runAnalysis: "Lancer l'analyse",
  },
  en: {
    dashboard: "Investment Analysis Dashboard",
    myPortfolio: "💼 My Portfolio",
    logout: "Logout",
    login: "🔐 Login / Register",
    optimizeBtn: "⚡ Optimize (Auto)",
    refresh: "↻ Refresh",
    reset: "Reset",
    totalValue: "Total Value",
    invested: "Invested",
    cash: "Cash",
    positions: "Positions",
    projection: "5-Year Projection",
    advice: "Advice",
    history: "History",
    buy: "Buy",
    sell: "Sell",
    loading: "Loading...",
    runAnalysis: "Run Analysis",
  },
  ar: {
    dashboard: "لوحة تحليل الاستثمار",
    myPortfolio: "💼 محفظتي",
    logout: "تسجيل خروج",
    login: "🔐 تسجيل الدخول / التسجيل",
    optimizeBtn: "⚡ تحسين (تلقائي)",
    refresh: "↻ تحديث",
    reset: "إعادة ضبط",
    totalValue: "القيمة الإجمالية",
    invested: "مستثمر",
    cash: "نقد",
    positions: "المراكز",
    projection: "توقعات 5 سنوات",
    advice: "نصائح",
    history: "تاريخ",
    buy: "شراء",
    sell: "بيع",
    loading: "جاري التحميل...",
    runAnalysis: "تشغيل التحليل",
  },
  zh: {
    dashboard: "投资分析仪表板",
    myPortfolio: "💼 我的投资组合",
    logout: "登出",
    login: "🔐 登录/注册",
    optimizeBtn: "⚡ 优化 (自动)",
    refresh: "↻ 刷新",
    reset: "重置",
    totalValue: "总价值",
    invested: "已投资",
    cash: "现金",
    positions: "头寸",
    projection: "5年预测",
    advice: "建议",
    history: "历史",
    buy: "买入",
    sell: "卖出",
    loading: "加载中...",
    runAnalysis: "运行分析",
  }
};

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState('fr');

  const t = (key) => {
    return translations[lang][key] || translations['en'][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      <div dir={lang === 'ar' ? 'rtl' : 'ltr'}>
        {children}
      </div>
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
