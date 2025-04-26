// import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
// import HomePage from './HomePage';
// import CategoryChatPage from './CategoryChatPage';

// function App() {
//   return (
//     <Router>
//       <Routes>
//         <Route path="/" element={<HomePage />} />
//         <Route path="/category/:city" element={<CategoryChatPage />} />
//       </Routes>
//     </Router>
//   );
// }

// export default App;



import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './HomePage';
import CategorySelectionPage from './CategorySelectionPage';
import CategoryChatPage from './CategoryChatPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/category/:city" element={<CategorySelectionPage />} />
        <Route path="/category/:city/:category" element={<CategoryChatPage />} />
      </Routes>
    </Router>
  );
}

export default App;