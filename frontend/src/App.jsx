import Header from "./components/Header";
import Hero from "./components/Hero";
import PosterChaupal from "./components/PosterChaupal";
import Infographics from "./components/Infographics";
import QuizCTA from "./components/QuizCTA";
import EventGallery from "./components/EventGallery";
import Commitments from "./components/Commitments";
import ClosingBanner from "./components/ClosingBanner";
import Footer from "./components/Footer";
import TickerBorder from "./components/TickerBorder";

export default function App() {
  return (
    <div className="min-h-screen">
      <TickerBorder />
      <Header />
      <main>
        <Hero />
        <PosterChaupal />
        <Infographics />
        <QuizCTA />
        <EventGallery />
        <Commitments />
        <ClosingBanner />
      </main>
      <Footer />
    </div>
  );
}
