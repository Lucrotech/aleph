import React, { lazy, Suspense } from 'react';
import { compose } from 'redux';
import { connect } from 'react-redux';

import AudioViewer from 'viewers/AudioViewer';
import DefaultViewer from 'viewers/DefaultViewer';
import TableViewer from 'viewers/TableViewer';
import TextViewer from 'viewers/TextViewer';
import HtmlViewer from 'viewers/HtmlViewer';
import ImageViewer from 'viewers/ImageViewer';
import FolderViewer from 'viewers/FolderViewer';
import EmailViewer from 'viewers/EmailViewer';
import VideoViewer from 'viewers/VideoViewer';
import ArticleViewer from 'viewers/ArticleViewer';
import withRouter from 'app/withRouter';
import { SectionLoading } from 'components/common';
import { selectEntityDirectionality } from 'selectors';
import queryString from 'query-string';

import './DocumentViewMode.scss';

const PdfViewer = lazy(() =>
  import(/* webpackChunkName: 'base' */ 'src/viewers/PdfViewer')
);

export class DocumentViewMode extends React.Component {
  shouldDisableSearch() {
    const { activeMode, textMode, location } = this.props;
    
    // Only disable search for view mode (not text mode) when in search preview
    if (activeMode === 'view' && !textMode && location) {
      const parsedHash = queryString.parse(location.hash);
      const parsedSearch = queryString.parse(location.search);
      
      // Check if we're in a search preview
      return !!(parsedHash['preview:id'] && parsedHash.q && (parsedSearch.q || parsedSearch.csq));
    }
    
    return false;
  }

  renderContent() {
    const { document, activeMode, dir, textMode } = this.props;
    const disableSearch = this.shouldDisableSearch();
    const processingError = document.getProperty('processingError');

    if (processingError && processingError.length) {
      return <DefaultViewer document={document} dir={dir} />;
    }

    if (document.schema.isA('Email')) {
      if (activeMode === 'browse') {
        return <FolderViewer document={document} dir={dir} />;
      }
      return (
        <EmailViewer document={document} activeMode={activeMode} dir={dir} />
      );
    }
    if (document.schema.isA('Image')) {
      if (activeMode === 'text') {
        return <TextViewer document={document} dir={dir} />;
      }
      return (
        <ImageViewer document={document} activeMode={activeMode} dir={dir} />
      );
    }
    if (document.schema.isA('Audio')) {
      return textMode ? (
        <TextViewer document={document} />
      ) : (
        <AudioViewer document={document} dir={dir} />
      );
    }

    if (document.schema.isA('Video')) {
      return textMode ? (
        <TextViewer document={document} />
      ) : (
        <VideoViewer document={document} dir={dir} />
      );
    }

    if (document.schema.isA('Table')) {
      return <TableViewer document={document} dir={dir} />;
    }
    if (document.schema.isA('PlainText')) {
      return <TextViewer document={document} dir={dir} />;
    }
    if (document.schema.isA('HyperText')) {
      return <HtmlViewer document={document} dir={dir} />;
    }
    if (document.schema.isA('Pages')) {
      return (
        <Suspense fallback={<SectionLoading />}>
          <PdfViewer 
            document={document} 
            activeMode={activeMode} 
            dir={dir}
            disableSearch={disableSearch}
          />
        </Suspense>
      );
    }
    if (document.schema.isA('Folder')) {
      return <FolderViewer document={document} dir={dir} />;
    }
    if (document.schema.isA('Article')) {
      return <ArticleViewer document={document} dir={dir} />;
    }
    return <DefaultViewer document={document} dir={dir} />;
  }

  render() {
    return <div className="DocumentViewMode">{this.renderContent()}</div>;
  }
}

const mapStateToProps = (state, ownProps) => {
  const { document } = ownProps;
  return {
    dir: selectEntityDirectionality(state, document),
  };
};

export default compose(withRouter, connect(mapStateToProps))(DocumentViewMode);
