import PaymentVerify from './components/PaymentVerify';

function App() {
  return (
    <Router>
      <div className="App">
        <Navbar />
        <Routes>
          <Route path="/payment/verify" element={<PaymentVerify />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App; 