import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api.js';

export default function ArticleReader({ articleId, onClose, lang = 'fa', t = (key) => key }) {
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function loadArticle() {
      if (!articleId) {
        setError(lang === 'fa' ? 'شناسه مقاله مشخص نشده است.' : 'No article identifier provided.');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await apiService.get(`/api/blog/${encodeURIComponent(articleId)}`);
        if (isMounted) {
          setArticle(data);
        }
      } catch (err) {
        if (isMounted) {
          console.error('Failed to load article:', err);
          setError(
            lang === 'fa'
              ? 'امکان بارگذاری مقاله وجود ندارد. ممکن است مقاله منتشر نشده یا حذف شده باشد.'
              : 'Unable to load article. It may be unpublished or restricted.'
          );
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadArticle();

    return () => {
      isMounted = false;
    };
  }, [articleId, lang]);

  return (
    <div
      className="article-reader-overlay"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(11, 15, 25, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '20px'
      }}
    >
      <div
        className="article-reader-modal card"
        style={{
          width: '100%',
          maxWidth: '800px',
          maxHeight: '90vh',
          overflowY: 'auto',
          margin: '0 auto',
          position: 'relative',
          padding: '30px',
          borderTop: '5px solid var(--primary)',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)'
        }}
      >
        {/* Header bar with Close action */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>
            {lang === 'fa' ? '📖 پژوهش و مقاله' : '📖 Research Article'}
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '4px 12px', fontSize: '0.9rem', cursor: 'pointer' }}
            onClick={onClose}
          >
            ✕ {lang === 'fa' ? 'بستن' : 'Close'}
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
            <div className="ai-pulse" style={{ margin: '0 auto 15px auto', width: '20px', height: '20px' }}></div>
            <p>{lang === 'fa' ? 'در حال بارگذاری مقاله...' : 'Loading article...'}</p>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div
            style={{
              padding: '20px',
              backgroundColor: 'rgba(194, 74, 62, 0.15)',
              border: '1px solid var(--danger)',
              borderRadius: '8px',
              textAlign: 'center',
              color: 'var(--text-main)',
              margin: '20px 0'
            }}
          >
            <p style={{ color: 'var(--danger)', fontWeight: 'bold', marginBottom: '10px' }}>⚠️ {error}</p>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ marginTop: '10px', fontSize: '0.85rem' }}
              onClick={onClose}
            >
              {lang === 'fa' ? 'بازگشت به فهرست مقالات' : 'Back to Articles'}
            </button>
          </div>
        )}

        {/* Render Article Content */}
        {!loading && !error && article && (
          <article className="article-content" style={{ color: 'var(--text-main)' }}>
            <h1 style={{ color: 'var(--primary)', marginTop: 0, marginBottom: '15px', lineHeight: '1.3', fontSize: '1.8rem' }}>
              {article.title}
            </h1>

            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '15px',
                fontSize: '0.85rem',
                color: 'var(--text-muted)',
                marginBottom: '20px',
                paddingBottom: '15px',
                borderBottom: '1px solid var(--border-dark)'
              }}
            >
              {article.author && <span>✍️ {article.author}</span>}
              {article.date && <span>📅 {article.date}</span>}
              {article.category && (
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(79, 70, 229, 0.15)',
                    color: 'var(--primary)',
                    fontWeight: 'bold'
                  }}
                >
                  🏷️ {article.category}
                </span>
              )}
            </div>

            {article.summary && (
              <div
                style={{
                  padding: '15px',
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  borderRight: lang === 'fa' ? '4px solid var(--primary)' : 'none',
                  borderLeft: lang !== 'fa' ? '4px solid var(--primary)' : 'none',
                  borderRadius: '4px',
                  marginBottom: '25px',
                  fontSize: '1rem',
                  lineHeight: '1.6',
                  color: 'var(--text-muted)',
                  fontStyle: 'italic'
                }}
              >
                {article.summary}
              </div>
            )}

            <div
              style={{
                fontSize: '1.05rem',
                lineHeight: '1.8',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                margin: '20px 0'
              }}
            >
              {article.content || article.summary || (lang === 'fa' ? 'محتوایی ثبت نشده است.' : 'No article content available.')}
            </div>

            {article.tags && Array.isArray(article.tags) && article.tags.length > 0 && (
              <div style={{ marginTop: '30px', paddingTop: '15px', borderTop: '1px solid var(--border-dark)' }}>
                {article.tags.map((tag, idx) => (
                  <span
                    key={idx}
                    style={{
                      fontSize: '0.8rem',
                      padding: '4px 10px',
                      background: 'rgba(79, 70, 229, 0.1)',
                      color: 'var(--primary)',
                      borderRadius: '4px',
                      marginRight: '6px',
                      marginLeft: '6px',
                      display: 'inline-block',
                      marginBottom: '6px'
                    }}
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </article>
        )}
      </div>
    </div>
  );
}
