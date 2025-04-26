import { useParams, useNavigate } from 'react-router-dom';
import './CategorySelectionPage.css';

function CategorySelectionPage() {
  const { city } = useParams();
  const navigate = useNavigate();
  const categories = ['Attractions', 'Hotels', 'Restaurants'];

  const handleCategorySelect = (category) => {
    navigate(`/category/${city}/${category.toLowerCase()}`);
  };

  return (
    <div className="category-selection-container">
      <h2 className="category-title">
        Choose a category to explore in {city.charAt(0).toUpperCase() + city.slice(1)}
      </h2>
      <div className="category-buttons">
        {categories.map((category) => (
          <button
            key={category}
            className="category-button"
            onClick={() => handleCategorySelect(category)}
          >
            {category}
          </button>
        ))}
      </div>
    </div>
  );
}

export default CategorySelectionPage;