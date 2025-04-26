import { useNavigate } from 'react-router-dom';
import './HomePage.css';

function HomePage() {
  const navigate = useNavigate();

  const cities = [
    { name: 'Kuala Lumpur', slug: 'kl' },
    { name: 'Langkawi', slug: 'langkawi' },
    { name: 'Penang', slug: 'penang' },
    { name: 'Melaka', slug: 'melaka' },
    { name: 'Johor Bahru', slug: 'johorbahru' },
    { name: 'Pahang', slug: 'pahang' },
    { name: 'Selangor', slug: 'selangor' },
    { name: 'Ipoh', slug: 'Ipoh' },
    { name: 'Sabah', slug: 'sabah' },
    { name: 'Putrajaya', slug: 'putrajaya' },
    { name: 'Sarawak', slug: 'sarawak' }
  ];

  return (
    <div className="home-container">
      {/* Navbar */}
      <nav className="navbar">
        <h1 className="navbar-title">TripMalaysia</h1>
        <div className="navbar-links">
          <a href="#about" className="navbar-link">About</a>
        </div>
      </nav>

      {/* Image Section */}
      <div className="image-container">
        <img src="/kuala-lumpur.png" alt="Malaysia" className="image" />
      </div>

      {/* Main Section */}
      <div className="content">
        <h2 className="main-title">Choose which city you want to explore in Malaysia</h2>
        <div className="slider-container">
          {cities.map((city) => (
            <button
              key={city.slug}
              onClick={() => navigate(`/category/${city.slug}`)}
              className="explore-button"
            >
              {city.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default HomePage;

