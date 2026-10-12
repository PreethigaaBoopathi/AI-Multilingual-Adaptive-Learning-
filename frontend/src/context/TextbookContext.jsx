import React, { createContext, useContext, useState, useEffect } from 'react';
import { textbookAPI } from '../services/api';

const TextbookContext = createContext();

export const TextbookProvider = ({ children }) => {
  const [textbooks, setTextbooks] = useState([]);
  const [activeTextbook, setActiveTextbook] = useState(null);
  const [activeChapter, setActiveChapter] = useState(null);
  const [activeSection, setActiveSection] = useState(null);
  const [language, setLanguage] = useState(() => {
    try {
      return localStorage.getItem('textiq_language') || 'en';
    } catch {
      return 'en';
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('textiq_language', language);
    } catch (e) {
      console.warn('Unable to persist language preference:', e);
    }
  }, [language]);

  useEffect(() => {
    const handleLangChange = () => {
      try {
        const stored = localStorage.getItem('textiq_language');
        if (stored && (stored === 'en' || stored === 'ta')) {
          setLanguage(stored);
        }
      } catch (e) {
        console.warn('Language sync error:', e);
      }
    };
    window.addEventListener('languageChange', handleLangChange);
    return () => window.removeEventListener('languageChange', handleLangChange);
  }, []);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('summary'); // 'summary', 'explain', 'visualize', 'ask', 'quiz', 'adaptive'

  const fetchTextbooks = async () => {
    try {
      setLoading(true);
      const data = await textbookAPI.getTextbooks();
      setTextbooks(data);
      if (data.length > 0 && !activeTextbook) {
        setActiveTextbook(data[0]);
        if (data[0].chapters && data[0].chapters.length > 0) {
          setActiveChapter(data[0].chapters[0]);
          if (data[0].chapters[0].sections && data[0].chapters[0].sections.length > 0) {
            setActiveSection(data[0].chapters[0].sections[0]);
          }
        }
      }
    } catch (err) {
      console.warn('API error fetching textbooks, fallback used:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTextbooks();
  }, []);

  const selectTextbook = (tb) => {
    setActiveTextbook(tb);
    if (tb.chapters && tb.chapters.length > 0) {
      setActiveChapter(tb.chapters[0]);
      if (tb.chapters[0].sections && tb.chapters[0].sections.length > 0) {
        setActiveSection(tb.chapters[0].sections[0]);
      } else {
        setActiveSection(null);
      }
    } else {
      setActiveChapter(null);
      setActiveSection(null);
    }
  };

  const selectChapter = (ch) => {
    setActiveChapter(ch);
    if (ch.sections && ch.sections.length > 0) {
      setActiveSection(ch.sections[0]);
    } else {
      setActiveSection(null);
    }
  };

  const deleteTextbook = async (id) => {
    try {
      setLoading(true);
      await textbookAPI.deleteTextbook(id);
      setTextbooks((prev) => {
        const remaining = prev.filter((tb) => tb.id !== id);
        if (activeTextbook?.id === id) {
          if (remaining.length > 0) {
            selectTextbook(remaining[0]);
          } else {
            setActiveTextbook(null);
            setActiveChapter(null);
            setActiveSection(null);
          }
        }
        return remaining;
      });
      return true;
    } catch (err) {
      console.error('Failed to remove textbook:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const clearAllTextbooks = async () => {
    try {
      setLoading(true);
      await textbookAPI.clearAllTextbooks();
      setTextbooks([]);
      setActiveTextbook(null);
      setActiveChapter(null);
      setActiveSection(null);
      return true;
    } catch (err) {
      console.error('Failed to clear textbooks:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return (
    <TextbookContext.Provider
      value={{
        textbooks,
        activeTextbook,
        activeChapter,
        activeSection,
        language,
        loading,
        error,
        activeTab,
        setActiveTab,
        setLanguage,
        selectTextbook,
        selectChapter,
        setActiveSection,
        fetchTextbooks,
        deleteTextbook,
        clearAllTextbooks,
      }}
    >
      {children}
    </TextbookContext.Provider>
  );
};

export const useTextbook = () => useContext(TextbookContext);
