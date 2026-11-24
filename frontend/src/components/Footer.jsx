import { Shield } from "lucide-react";
import { appUrl } from "../config";

export default function Footer() {
  return (
    <footer className="bg-peacock-dark text-ivory/80">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
        <div className="sm:col-span-2 lg:col-span-1">
          <p className="mb-2 flex items-center gap-2 font-heading text-lg font-extrabold text-white">
            <Shield className="h-5 w-5 text-gold" /> CleanClick
          </p>
          <p className="text-sm">
            Practical, hands-on cyber security awareness &mdash; lessons, quizzes, phishing practice and current
            cybercrime news, all in one street-smart portal.
          </p>
        </div>
        <div>
          <h4 className="mb-3 text-xs font-bold uppercase tracking-widest text-gold-light">Explore</h4>
          <a className="mb-2 block text-sm hover:text-gold-light" href="#posters">Posters</a>
          <a className="mb-2 block text-sm hover:text-gold-light" href="#infographics">Infographics</a>
          <a className="mb-2 block text-sm hover:text-gold-light" href={appUrl("/films")}>Films</a>
        </div>
        <div>
          <h4 className="mb-3 text-xs font-bold uppercase tracking-widest text-gold-light">Stay safe</h4>
          <a className="mb-2 block text-sm hover:text-gold-light" href={appUrl("/phishing")}>Phishing practice</a>
          <a className="mb-2 block text-sm hover:text-gold-light" href={appUrl("/news")}>Cyber news</a>
          <a className="mb-2 block text-sm hover:text-gold-light" href={appUrl("/certificates")}>Certificates</a>
        </div>
        <div>
          <h4 className="mb-3 text-xs font-bold uppercase tracking-widest text-gold-light">Account</h4>
          <a className="mb-2 block text-sm hover:text-gold-light" href={appUrl("/login")}>Sign in</a>
          <a className="mb-2 block text-sm hover:text-gold-light" href={appUrl("/register")}>Register</a>
        </div>
      </div>
      <div className="border-t border-white/10 px-4 py-4 text-center text-xs sm:px-6">
        &copy; CleanClick Cyber Awareness Portal &middot; Watch, Learn, Click Clean
      </div>
    </footer>
  );
}
