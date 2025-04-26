// export default CategoryChatPage;
import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import './CategoryChatPage.css';

function CategoryChatPage() {
  const { city, category } = useParams();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [likedItems, setLikedItems] = useState({});
  const [chatHistory, setChatHistory] = useState([]);
  const [allSuggestions, setAllSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);

  // Initialize with a welcome message when component mounts
  useEffect(() => {
    setChatHistory([
      { 
        sender: 'bot', 
        text: `You can now start asking about ${category} in ${city.charAt(0).toUpperCase() + city.slice(1)}.` 
      }
    ]);
  }, [city, category]);

  const handleQuery = async (e) => {
    e?.preventDefault();
    
    if (!query || !category) return;

    setChatHistory((prev) => [...prev, { sender: 'user', text: query }]);
    setLoading(true);

    try {
      const res = await fetch(`http://localhost:5000/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          city, 
          category, 
          query,
          liked: Object.keys(likedItems).filter(item => likedItems[item])
        }),
      });

      const data = await res.json();
      
      if (data.suggestions && data.suggestions.length > 0) {
        setAllSuggestions(data.suggestions);
        
        setChatHistory((prev) => [
          ...prev,
          {
            sender: 'bot',
            text: `Here are some ${category} in ${city}:`,
            suggestions: data.suggestions,
            hasMore: data.total_results > data.suggestions.length,
            shownCount: data.suggestions.length,
            totalCount: data.total_results,
            originalQuery: query
          },
        ]);
      } else if (data.response) {
        setChatHistory((prev) => [...prev, { sender: 'bot', text: data.response }]);
      } else if (data.error) {
        setChatHistory((prev) => [...prev, { sender: 'bot', text: `Error: ${data.error}` }]);
      } else {
        setChatHistory((prev) => [...prev, { 
          sender: 'bot', 
          text: "I couldn't find anything matching your query. Try asking differently." 
        }]);
      }
    } catch (error) {
      console.error("API request failed:", error);
      setChatHistory((prev) => [...prev, { 
        sender: 'bot', 
        text: "Sorry, there was an error processing your request. Please try again." 
      }]);
    } finally {
      setLoading(false);
    }

    setQuery('');
  };

  const handleShowMore = async (messageIndex) => {
    const message = chatHistory[messageIndex];
    if (!message || !message.hasMore) return;

    try {
      setLoading(true);
      
      const res = await fetch(`http://localhost:5000/show_more`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          city, 
          category, 
          query: message.originalQuery,
          offset: message.shownCount,
          limit: 2
        }),
      });

      const data = await res.json();
      
      if (data.suggestions && data.suggestions.length > 0) {
        const updatedMessage = {
          ...message,
          suggestions: [...message.suggestions, ...data.suggestions],
          shownCount: message.shownCount + data.suggestions.length,
          hasMore: message.shownCount + data.suggestions.length < data.total_results
        };

        setChatHistory(prev => [
          ...prev.slice(0, messageIndex),
          updatedMessage,
          ...prev.slice(messageIndex + 1)
        ]);
      }
    } catch (error) {
      console.error("Error loading more results:", error);
      setChatHistory(prev => [
        ...prev,
        { sender: 'bot', text: "Sorry, couldn't load more results. Please try again." }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleLike = async (itemName) => {
    try {
      await fetch('http://localhost:5000/like', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city, category, name: itemName }),
      });

      setLikedItems((prev) => ({ ...prev, [itemName]: true }));
      
      setChatHistory((prev) => 
        prev.map(entry => {
          if (entry.suggestions) {
            return {
              ...entry,
              suggestions: entry.suggestions.map(suggestion => 
                suggestion.name === itemName 
                  ? { ...suggestion, liked: true, likes: (suggestion.likes || 0) + 1 } 
                  : suggestion
              )
            };
          }
          return entry;
        })
      );
    } catch (error) {
      console.error("Failed to like item:", error);
    }
  };

  const handleDislike = async (itemName) => {
    try {
      await fetch('http://localhost:5000/dislike', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city, category, name: itemName }),
      });

      setLikedItems((prev) => {
        const updated = { ...prev };
        delete updated[itemName];
        return updated;
      });
      
      setChatHistory((prev) => 
        prev.map(entry => {
          if (entry.suggestions) {
            return {
              ...entry,
              suggestions: entry.suggestions.map(suggestion => 
                suggestion.name === itemName 
                  ? { ...suggestion, liked: false } 
                  : suggestion
              )
            };
          }
          return entry;
        })
      );
    } catch (error) {
      console.error("Failed to dislike item:", error);
    }
  };

  return (
    <div className="category-chat-container">
      <div className="chatbot-wrapper">
        <div className="chatbot-header">
          <h2 className="chatbot-title">
            You can now start asking about <strong>{category}</strong> in <strong>{city}</strong>
          </h2>
          <button 
            onClick={() => navigate(`/category/${city}`)}
            className="back-button"
          >
            ← Back to Categories
          </button>
        </div>

        <div className="chatbot-section">
          <div className="chat-ui">
            <div className="chat-response-container">
              {chatHistory.map((entry, idx) => (
                <div key={idx} className={`chat-message ${entry.sender}`}>
                  <p className="chat-text">{entry.text}</p>

                  {entry.suggestions &&
                    entry.suggestions.map((item, subIdx) => (
                      <div key={subIdx} className="chat-suggestion">
                        <h3 className="chat-suggestion-title">{item.name}</h3>
                        <p>{item.description}</p>
                        <p>📍 {item.address}</p>
                        {item.reviews?.startsWith('http') ? (
                          <p>
                            ⭐ Reviews:{' '}
                            <a href={item.reviews} target="_blank" rel="noopener noreferrer">
                              Read Reviews
                            </a>
                          </p>
                        ) : (
                          <p>⭐ Reviews: {item.reviews}</p>
                        )}
                        {item.website && (
                          <p>
                            🌐 Website:{' '}
                            <a href={item.website} target="_blank" rel="noopener noreferrer">
                              Visit Website
                            </a>
                          </p>
                        )}
                        {item.relevance !== undefined && (
                          <p className="relevance-score">🔍 Relevance Score: {item.relevance.toFixed(2)}</p>
                        )}
                        <div className="like-buttons">
                          {likedItems[item.name] ? (
                            <div className="liked-indicator">❤️ Liked</div>
                          ) : (
                            <button 
                              onClick={() => handleLike(item.name)} 
                              className="like-btn"
                            >
                              👍 Like
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  
                  {entry.hasMore && (
                    <button 
                      onClick={() => handleShowMore(idx)} 
                      className="chat-button show-more-btn"
                    >
                      Show more ({entry.totalCount - entry.shownCount} remaining)
                    </button>
                  )}
                </div>
              ))}

              {loading && (
                <div className="chat-message bot loading-msg">
                  <p className="chat-text">⏳ Loading...</p>
                </div>
              )}
            </div>

            <form onSubmit={handleQuery} className="chat-query-container">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask me something..."
                className="chat-input"
              />
              <button type="submit" className="chat-button">
                Ask
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CategoryChatPage;