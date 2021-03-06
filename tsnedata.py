import numpy as np
from random import shuffle
import textutils
import ioutils


def get_doc_indices_for_sne():
    num_select_docs = -1
    docs_list_file = 'e:/dc/nyt-world-full/processed/test/doclist.txt'
    dst_file = 'e:/dc/nyt-world-full/processed/test/sne-doc-indices-all.bin'
    num_docs = textutils.get_num_lines_in_file(docs_list_file)
    indices_list = range(num_docs)
    shuffle(indices_list)
    picked_indices = sorted(indices_list[:num_select_docs])
    print picked_indices[:100]
    fout = open(dst_file, 'wb')
    np.asarray([len(picked_indices)], np.int32).tofile(fout)
    np.asarray(picked_indices, np.int32).tofile(fout)
    fout.close()


def doc_vecs_file_for_tsne():
    tag = 'all'
    vecs_file_tag = '012'
    all_doc_vecs_file = 'e:/dc/nyt-world-full/processed/vecs/dedw4-vecs-%s.bin' % vecs_file_tag
    all_doc_labels_file = 'e:/dc/nyt-world-full/processed/test/doc-labels.bin'
    doc_indices_file = 'e:/dc/nyt-world-full/processed/test/sne-doc-indices-%s.bin' % tag
    dst_doc_vecs_file = 'e:/dc/nyt-world-full/processed/test/sne-emadr-vecs-%s-%s.txt' % (vecs_file_tag, tag)
    dst_labels_file = 'e:/dc/nyt-world-full/processed/test/sne-doc-labels-%s.txt' % tag

    fin = open(doc_indices_file, 'rb')
    num_indices = np.fromfile(fin, np.int32, 1)
    doc_indices = np.fromfile(fin, np.int32, num_indices)
    fin.close()

    doc_vecs = ioutils.load_vec_list_file(all_doc_vecs_file)
    fout_vecs = open(dst_doc_vecs_file, 'wb')
    for idx in doc_indices:
        for v in doc_vecs[idx]:
            fout_vecs.write('   %f' % v)
        fout_vecs.write('\n')
    fout_vecs.close()

    # labels = ioutils.load_labels_file(all_doc_labels_file)
    # fout_labels = open(dst_labels_file, 'wb')
    # for idx in doc_indices:
    #     fout_labels.write('%d\n' % labels[idx])
    # fout_labels.close()


if __name__ == '__main__':
    # get_doc_indices_for_sne()
    doc_vecs_file_for_tsne()
