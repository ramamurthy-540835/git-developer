export default function PublishButtons({ onDownload, onCopy, onPr }) {
  return <div className='publish-row'><button className='btn' onClick={onDownload}>📥 Download</button><button className='btn' onClick={onCopy}>📋 Copy</button><button className='btn btn-primary' onClick={onPr}>🔀 Create PR</button></div>;
}
