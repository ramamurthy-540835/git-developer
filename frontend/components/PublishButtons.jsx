export default function PublishButtons({ onDownload, onCopy, onPr }) {
  return <div className='publish-row'>
    <button className='btn btn-compact' onClick={onDownload}><span className='btn-icon'>↓</span>Download</button>
    <button className='btn btn-compact' onClick={onCopy}><span className='btn-icon'>⧉</span>Copy</button>
    <button className='btn btn-primary btn-compact' onClick={onPr}><span className='btn-icon'>PR</span>Create PR</button>
  </div>;
}
