import './globals.css';
import '../styles/components.css';
import Header from '../components/Header';

export const metadata = { title: 'git-developer README Generator' };

export default function RootLayout({ children }) {
  return (
    <html lang='en'>
      <body>
        <div className='app-shell'>
          <Header />
          <main className='main-wrap'>{children}</main>
        </div>
      </body>
    </html>
  );
}
